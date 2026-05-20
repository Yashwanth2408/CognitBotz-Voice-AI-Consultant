"""
audio/speech_to_text.py
-----------------------
Automatic Speech Recognition using Faster Whisper.

Design rationale:
  - Faster Whisper selected per spec section 7 for GPU-accelerated, local ASR.
  - 'small.en' model balances speed and accuracy for English enterprise queries.
  - int8 compute type on CPU significantly reduces inference time vs float32.
  - Model is loaded once and cached to avoid repeated cold-start overhead.
  - WAV bytes are written to a temp file — Faster Whisper requires a file path.
"""

import io
import os
import tempfile
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import numpy as np

from config.settings import (
    AUDIO_SAMPLE_RATE,
    WHISPER_MODEL_SIZE,
    WHISPER_COMPUTE_TYPE,
)
from utils.logger import get_logger
from utils.helpers import numpy_to_wav_bytes

logger = get_logger(__name__)


@dataclass
class TranscriptionResult:
    """Structured output from a Faster Whisper transcription."""
    text: str                   # Full transcribed text
    language: str               # Detected language code (e.g., "en")
    duration_sec: float         # Transcription processing time
    confidence: float           # Average segment confidence [0, 1]
    is_empty: bool              # True if no speech was detected

    @property
    def clean_text(self) -> str:
        """Transcript with leading/trailing whitespace removed."""
        return self.text.strip()


@lru_cache(maxsize=1)
def _load_whisper_model():
    """
    Load Faster Whisper model once and cache for process lifetime.

    Model selection: 'small.en' per spec §7.
    - 'small.en' is English-only, making it faster than the multilingual 'small'.
    - 'int8' compute type halves memory usage and speeds up CPU inference.
    - GPU (float16) is used automatically if CUDA is available.

    Returns:
        Loaded WhisperModel instance.
    """
    from faster_whisper import WhisperModel  # type: ignore

    device = "cuda" if _cuda_available() else "cpu"
    compute_type = "float16" if device == "cuda" else WHISPER_COMPUTE_TYPE

    logger.info(
        f"Loading Faster Whisper model: {WHISPER_MODEL_SIZE} "
        f"(device={device}, compute_type={compute_type})"
    )

    model = WhisperModel(
        WHISPER_MODEL_SIZE,
        device=device,
        compute_type=compute_type,
    )

    logger.info("Faster Whisper model loaded successfully.")
    return model


def _cuda_available() -> bool:
    """Check for CUDA availability without hard-requiring torch."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


class SpeechToText:
    """
    Speech recognition engine wrapping Faster Whisper.

    Transcribes WAV audio bytes to text. Handles the temp-file
    lifecycle required by Faster Whisper's file-path API.
    """

    def __init__(self) -> None:
        """Load the Whisper model (first call triggers download ~140 MB)."""
        self._model = _load_whisper_model()
        logger.info("SpeechToText initialised.")

    def transcribe(
        self,
        audio_input: bytes | np.ndarray,
        sample_rate: int = AUDIO_SAMPLE_RATE,
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.

        Accepts either WAV bytes (e.g., from AudioRecorder) or a raw
        float32 numpy array. Converts numpy arrays to WAV internally.

        Args:
            audio_input: WAV bytes or float32 numpy array at 16kHz.
            sample_rate: Sample rate of the numpy array (if provided).

        Returns:
            TranscriptionResult with text, language, and confidence.
        """
        start = time.perf_counter()

        # Normalise input to WAV bytes
        if isinstance(audio_input, np.ndarray):
            wav_bytes = numpy_to_wav_bytes(audio_input, sample_rate)
        else:
            wav_bytes = audio_input

        if not wav_bytes or len(wav_bytes) < 100:
            return TranscriptionResult(
                text="", language="en", duration_sec=0.0,
                confidence=0.0, is_empty=True,
            )

        # Write WAV to a named temp file — Faster Whisper requires file path
        with tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(wav_bytes)

        try:
            segments, info = self._model.transcribe(
                tmp_path,
                language="en",             # Force English for enterprise context
                beam_size=5,               # Balance accuracy vs speed
                best_of=5,
                vad_filter=True,           # Built-in VAD pre-filtering
                vad_parameters={
                    "min_silence_duration_ms": 500,
                    "speech_pad_ms": 200,
                },
            )

            # Materialise the generator — segments are lazy by default
            segment_list = list(segments)
            full_text = " ".join(seg.text for seg in segment_list).strip()

            # Average confidence across all segments
            avg_confidence = (
                sum(
                    getattr(seg, "avg_logprob", -0.5)
                    for seg in segment_list
                ) / len(segment_list)
                if segment_list else -1.0
            )
            # Convert log-probability to [0, 1] range
            confidence = float(np.clip(np.exp(avg_confidence), 0.0, 1.0))

            elapsed = time.perf_counter() - start
            is_empty = len(full_text) == 0

            logger.info(
                f"Transcription: '{full_text[:80]}' "
                f"(lang={info.language}, conf={confidence:.2f}, {elapsed:.2f}s)"
            )

            return TranscriptionResult(
                text=full_text,
                language=info.language or "en",
                duration_sec=elapsed,
                confidence=confidence,
                is_empty=is_empty,
            )

        except Exception as exc:
            logger.error(f"Transcription failed: {exc}", exc_info=True)
            return TranscriptionResult(
                text="", language="en", duration_sec=0.0,
                confidence=0.0, is_empty=True,
            )
        finally:
            # Always clean up the temp file to prevent disk accumulation
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
