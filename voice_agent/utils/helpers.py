"""
utils/helpers.py
----------------
General-purpose utility functions used across the application.

Design rationale:
  - Text normalisation for TTS ensures spoken responses sound natural.
  - Audio utilities centralise WAV I/O to avoid repetition.
  - All functions are pure (no side effects) and independently testable.
"""

import io
import re
import wave
import base64
import struct
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# Text Utilities
# ─────────────────────────────────────────────

def normalize_text_for_tts(text: str) -> str:
    """
    Clean LLM output for natural voice synthesis.

    The LLM may produce markdown-formatted text that sounds unnatural
    when read aloud (e.g., '**bold**', '# Header', bullet '•').
    This function strips all such artefacts.

    Args:
        text: Raw LLM response text.

    Returns:
        Clean, speakable plain text.
    """
    # Remove markdown bold/italic markers
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)

    # Remove markdown headers (# ## ###)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Replace bullet points with sentence breaks (natural pauses when spoken)
    text = re.sub(r"^\s*[-•*]\s+", "", text, flags=re.MULTILINE)

    # Remove markdown links [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove inline code backticks
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)

    # Make common symbols speakable before ASCII cleanup.
    text = re.sub(r"\s*&\s*", " and ", text)
    text = re.sub(r"\s*\+\s*", " plus ", text)
    text = re.sub(r"\s*;\s*", ". ", text)
    text = re.sub(r"\s*:\s+", ". ", text)

    # Remove horizontal rules
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)

    # Line breaks become sentence boundaries (avoids run-on lists)
    text = re.sub(r"\n+", ". ", text)

    # Normalize unicode characters (e.g., smart quotes → straight)
    text = unicodedata.normalize("NFKD", text)

    # Remove non-ASCII characters that TTS cannot pronounce
    text = text.encode("ascii", errors="ignore").decode("ascii")

    # Clean punctuation spacing for smoother phrasing
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"([,.!?])([^\s])", r"\1 \2", text)
    text = re.sub(r"\.{2,}", ".", text)

    if text and text[-1] not in ".!?":
        text = f"{text}."

    return text.strip()


def truncate_text(text: str, max_chars: int = 500) -> str:
    """
    Truncate text at the last complete sentence boundary.

    Used to enforce TTS response length limits without cutting mid-sentence.

    Args:
        text: Input text.
        max_chars: Maximum character count.

    Returns:
        Truncated text ending at a sentence boundary.
    """
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    # Find the last sentence-ending punctuation
    last_period = max(
        truncated.rfind("."),
        truncated.rfind("!"),
        truncated.rfind("?"),
    )

    if last_period > max_chars // 2:
        return truncated[: last_period + 1]

    return truncated + "..."


def format_timestamp() -> str:
    """Return current ISO 8601 timestamp for log entries and file naming."""
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def sanitize_filename(name: str) -> str:
    """
    Convert arbitrary text to a safe filename component.

    Args:
        name: Raw string (e.g., user query).

    Returns:
        Lowercase alphanumeric-and-hyphen filename fragment.
    """
    name = re.sub(r"[^\w\s-]", "", name.lower())
    name = re.sub(r"[\s_]+", "-", name)
    return name[:50]  # Cap length to avoid filesystem issues


# ─────────────────────────────────────────────
# Audio Utilities
# ─────────────────────────────────────────────

def numpy_to_wav_bytes(
    audio: np.ndarray,
    sample_rate: int,
    sample_width: int = 2,
) -> bytes:
    """
    Convert a float32 NumPy audio array to WAV file bytes.

    Args:
        audio: Float32 audio samples, values in [-1.0, 1.0].
        sample_rate: Sample rate in Hz.
        sample_width: Bytes per sample (2 = 16-bit PCM).

    Returns:
        WAV-formatted bytes ready for file write or st.audio().
    """
    # Scale float32 [-1, 1] to int16 range
    audio_int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())

    return buffer.getvalue()


def wav_bytes_to_numpy(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    """
    Parse WAV bytes into a float32 NumPy array.

    Args:
        wav_bytes: Raw WAV file bytes.

    Returns:
        Tuple of (float32 audio array, sample_rate).
    """
    buffer = io.BytesIO(wav_bytes)
    with wave.open(buffer, "rb") as wf:
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        sample_width = wf.getsampwidth()
        raw_bytes = wf.readframes(n_frames)

    # Determine dtype from sample width
    dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sample_width, np.int16)
    audio_int = np.frombuffer(raw_bytes, dtype=dtype)

    # Normalise to float32 [-1, 1]
    audio_float = audio_int.astype(np.float32) / np.iinfo(dtype).max

    return audio_float, sample_rate


def audio_bytes_to_base64(audio_bytes: bytes) -> str:
    """
    Encode WAV bytes as base64 string for embedding in Streamlit HTML.

    Args:
        audio_bytes: WAV file content.

    Returns:
        Base64-encoded string.
    """
    return base64.b64encode(audio_bytes).decode("utf-8")


def load_wav_file(path: Path) -> tuple[np.ndarray, int]:
    """
    Load a WAV file from disk into a float32 NumPy array.

    Args:
        path: Filesystem path to the WAV file.

    Returns:
        Tuple of (float32 audio array, sample_rate).

    Raises:
        FileNotFoundError: If the WAV file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"WAV file not found: {path}")

    with open(path, "rb") as f:
        return wav_bytes_to_numpy(f.read())


def save_wav_file(audio: np.ndarray, sample_rate: int, path: Path) -> None:
    """
    Write a float32 NumPy array to disk as a 16-bit PCM WAV file.

    Args:
        audio: Float32 audio samples.
        sample_rate: Sample rate in Hz.
        path: Destination file path (parent directories created automatically).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    wav_bytes = numpy_to_wav_bytes(audio, sample_rate)
    path.write_bytes(wav_bytes)
    logger.debug(f"Saved WAV file: {path} ({len(wav_bytes)} bytes)")


def generate_silence_wav(duration_sec: float, sample_rate: int = 16000) -> bytes:
    """
    Generate a silent WAV file of the specified duration.

    Used as a placeholder when no real voice output is available.
    Piper will fall back to silence if synthesis fails.

    Args:
        duration_sec: Duration of silence in seconds.
        sample_rate: Sample rate in Hz.

    Returns:
        WAV-formatted bytes containing silence.
    """
    n_samples = int(duration_sec * sample_rate)
    silence = np.zeros(n_samples, dtype=np.float32)
    return numpy_to_wav_bytes(silence, sample_rate)
