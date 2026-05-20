"""
audio/text_to_speech.py
-----------------------
Fully offline voice synthesis.

Default engine: MMS VITS (onecxi/mms-english-female-indic)
  - English speech with an Indian female speaker (IndicTTS-trained)
  - Runs locally via Hugging Face Transformers after one-time model download

Fallback engine: Piper ONNX (en_IN-spicor-medium)
  - Indian English accent, fast CPU inference
  - Set TTS_ENGINE=piper in .env to use Piper only
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np
import torch
from transformers import AutoTokenizer, VitsModel

from config.settings import (
    TTS_AUTO_DOWNLOAD,
    TTS_ENGINE,
    TTS_LENGTH_SCALE,
    TTS_MMS_MODEL_ID,
    TTS_MODEL_PATH,
    TTS_SENTENCE_PAUSE_SEC,
    TTS_VOICES_DIR,
)
from utils.helpers import generate_silence_wav, numpy_to_wav_bytes
from utils.logger import get_logger

logger = get_logger(__name__)

_MIN_MODEL_BYTES = 1_000_000


@dataclass(frozen=True)
class SynthesisResult:
    """Structured output from a TTS synthesis operation."""
    wav_bytes: bytes
    duration_sec: float
    text_length: int
    sample_rate: int


@dataclass
class _MmsVoice:
    """Loaded MMS VITS model for Indian female English."""
    model: VitsModel
    tokenizer: AutoTokenizer
    sample_rate: int


def _split_into_sentences(text: str) -> list[str]:
    """
    Split text into individual sentences for natural prosody.

    Each sentence is synthesised separately with a short pause between,
    which produces much more natural speech than one long utterance.
    """
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return []

    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    sentences: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part[-1] not in ".!?":
            part = f"{part}."
        sentences.append(part)
    return sentences


def _trim_edge_silence(
    audio: np.ndarray,
    sample_rate: int,
    threshold: float = 0.008,
    keep_ms: int = 12,
) -> np.ndarray:
    """Trim leading/trailing silence from a segment."""
    if audio.size == 0:
        return audio

    mask = np.abs(audio) > threshold
    if not np.any(mask):
        return audio

    start = int(np.argmax(mask))
    end = int(len(audio) - np.argmax(mask[::-1]))
    keep = int(sample_rate * keep_ms / 1000)
    start = max(0, start - keep)
    end = min(len(audio), end + keep)
    return audio[start:end]


def _join_segments_with_pauses(
    segments: list[np.ndarray],
    sample_rate: int,
    pause_sec: float = TTS_SENTENCE_PAUSE_SEC,
) -> np.ndarray:
    """Join sentence audio with a short natural pause between each."""
    if not segments:
        return np.array([], dtype=np.float32)
    if len(segments) == 1:
        return segments[0]

    pause = np.zeros(int(sample_rate * pause_sec), dtype=np.float32)
    parts: list[np.ndarray] = []
    for idx, segment in enumerate(segments):
        if segment.size == 0:
            continue
        parts.append(segment)
        if idx < len(segments) - 1:
            parts.append(pause)
    return np.concatenate(parts) if parts else np.array([], dtype=np.float32)


def _normalize_audio(audio: np.ndarray, target_peak: float = 0.92) -> np.ndarray:
    """Apply a single gentle normalization pass to the full utterance."""
    if audio.size == 0:
        return audio
    peak = float(np.max(np.abs(audio)))
    if peak < 1e-8:
        return audio
    return np.clip(audio * (target_peak / peak), -1.0, 1.0).astype(np.float32)


# ─────────────────────────────────────────────
# MMS VITS (default — Indian female English, offline)
# ─────────────────────────────────────────────


def _load_mms_model() -> Optional[_MmsVoice]:
    """Load the MMS VITS model from local cache or Hugging Face hub."""
    try:
        logger.info("Loading MMS TTS model: %s (offline after download)", TTS_MMS_MODEL_ID)
        model = VitsModel.from_pretrained(TTS_MMS_MODEL_ID)
        tokenizer = AutoTokenizer.from_pretrained(TTS_MMS_MODEL_ID)
        model.eval()
        sample_rate = int(model.config.sampling_rate)
        logger.info("MMS TTS ready (sample_rate=%s)", sample_rate)
        return _MmsVoice(model=model, tokenizer=tokenizer, sample_rate=sample_rate)
    except Exception as exc:
        logger.error("Failed to load MMS TTS: %s", exc, exc_info=True)
        return None


def _synthesize_mms_sentence(voice: _MmsVoice, text: str) -> np.ndarray:
    """Synthesise a single sentence with MMS VITS (one sentence = natural prosody)."""
    inputs = voice.tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        waveform = voice.model(**inputs).waveform

    audio = waveform.squeeze().cpu().numpy().astype(np.float32)
    return _trim_edge_silence(audio, voice.sample_rate)


# ─────────────────────────────────────────────
# Piper ONNX (fallback — Indian English, offline)
# ─────────────────────────────────────────────


def _piper_model_paths() -> tuple[Path, Path]:
    model_path = Path(TTS_MODEL_PATH)
    return model_path, Path(f"{model_path}.json")


def ensure_piper_voice_model() -> bool:
    """Ensure Piper ONNX model files exist (optional fallback engine)."""
    model_path, config_path = _piper_model_paths()

    if TTS_AUTO_DOWNLOAD and (
        not model_path.exists() or model_path.stat().st_size < _MIN_MODEL_BYTES
    ):
        try:
            from piper.download_voices import download_voice

            voice_id = model_path.stem
            logger.info("Downloading Piper voice: %s", voice_id)
            download_voice(voice_id, TTS_VOICES_DIR)
        except Exception as exc:
            logger.error("Failed to download Piper voice: %s", exc)

    return (
        model_path.exists()
        and model_path.stat().st_size >= _MIN_MODEL_BYTES
        and config_path.exists()
    )


def _load_piper_model():
    """Load Piper voice when TTS_ENGINE=piper or as MMS fallback."""
    from piper import PiperVoice
    from piper.config import SynthesisConfig

    if TTS_AUTO_DOWNLOAD:
        ensure_piper_voice_model()

    model_path, config_path = _piper_model_paths()
    if not model_path.exists():
        return None

    try:
        voice = PiperVoice.load(model_path, config_path=config_path, use_cuda=False)
        return voice, SynthesisConfig(
            length_scale=TTS_LENGTH_SCALE,
            volume=1.0,
            normalize_audio=True,
        )
    except Exception as exc:
        logger.error("Failed to load Piper voice: %s", exc, exc_info=True)
        return None


def _synthesize_piper_text(voice, syn_config, text: str) -> tuple[np.ndarray, int]:
    """
    Synthesise full text with Piper.

    Piper yields one audio segment per sentence internally — best for natural flow.
    """
    sentence_chunks = list(voice.synthesize(text, syn_config=syn_config))
    if not sentence_chunks:
        raise RuntimeError("Piper returned no audio")

    sample_rate = sentence_chunks[0].sample_rate
    segments = [
        _trim_edge_silence(chunk.audio_float_array, sample_rate)
        for chunk in sentence_chunks
    ]
    combined = _join_segments_with_pauses(segments, sample_rate)
    return _normalize_audio(combined), sample_rate


def _synthesize_mms_text(voice: _MmsVoice, text: str) -> tuple[np.ndarray, int]:
    """Synthesise full text sentence-by-sentence with MMS VITS."""
    sentences = _split_into_sentences(text)
    if not sentences:
        raise RuntimeError("No sentences to synthesise")

    segments: list[np.ndarray] = []
    for sentence in sentences:
        segments.append(_synthesize_mms_sentence(voice, sentence))

    combined = _join_segments_with_pauses(segments, voice.sample_rate)
    return _normalize_audio(combined), voice.sample_rate


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────


def is_tts_configured() -> bool:
    """Return True when the configured offline TTS engine can run."""
    if TTS_ENGINE == "piper":
        return ensure_piper_voice_model()
    # MMS loads from Hugging Face cache; assume available if engine is mms
    return True


def is_piper_configured() -> bool:
    """Backward-compatible alias used by tests and diagnostics."""
    return ensure_piper_voice_model()


def _load_tts_model() -> Union[_MmsVoice, tuple, None]:
    """Compatibility hook for tests — returns the active voice backend."""
    if TTS_ENGINE == "piper":
        return _load_piper_model()
    return _load_mms_model()


class TextToSpeech:
    """
    Offline voice synthesis.

    Default: MMS VITS Indian female English (onecxi/mms-english-female-indic).
    Fallback: Piper en_IN-spicor if MMS load fails.
    """

    def __init__(self) -> None:
        """Preload the configured offline TTS model."""
        self._engine = TTS_ENGINE
        self._mms: Optional[_MmsVoice] = None
        self._piper = None
        self._piper_config = None

        if self._engine == "mms":
            self._mms = _load_mms_model()
            if self._mms is None:
                logger.warning("MMS TTS failed to load; trying Piper fallback")
                self._load_piper_fallback()
        else:
            self._load_piper_fallback()

        if self._mms is not None:
            logger.info("TextToSpeech ready: MMS Indian female English (%s)", TTS_MMS_MODEL_ID)
        elif self._piper is not None:
            logger.info("TextToSpeech ready: Piper (%s)", TTS_MODEL_PATH)
        else:
            logger.warning("No offline TTS model loaded; responses will be silent")

    def _load_piper_fallback(self) -> None:
        loaded = _load_piper_model()
        if loaded is not None:
            self._piper, self._piper_config = loaded
            self._engine = "piper"

    def synthesise(self, text: str) -> SynthesisResult:
        """
        Synthesise text to WAV audio (fully offline).

        Args:
            text: Clean text to synthesise (no markdown).

        Returns:
            SynthesisResult with audio bytes and metadata.
        """
        if not text or not text.strip():
            logger.info("TTS: Empty text, returning silence")
            silence = generate_silence_wav(0.5)
            return SynthesisResult(
                wav_bytes=silence,
                duration_sec=0.0,
                text_length=0,
                sample_rate=16000,
            )

        if self._mms is None and self._piper is None:
            logger.error("TTS: No offline model loaded; returning silence")
            silence = generate_silence_wav(1.0)
            return SynthesisResult(
                wav_bytes=silence,
                duration_sec=0.0,
                text_length=len(text),
                sample_rate=16000,
            )

        start = time.perf_counter()
        logger.info("TTS [%s]: Starting synthesis for %s chars", self._engine, len(text))

        try:
            if self._mms is not None:
                combined_audio, sample_rate = _synthesize_mms_text(self._mms, text)
            else:
                combined_audio, sample_rate = _synthesize_piper_text(
                    self._piper, self._piper_config, text
                )

            if combined_audio.size == 0:
                raise RuntimeError("TTS returned no audio")

            audio_wav = numpy_to_wav_bytes(combined_audio, sample_rate=sample_rate)
            elapsed = time.perf_counter() - start

            if audio_wav and len(audio_wav) > 100:
                logger.info(
                    "TTS [%s]: Success in %.2fs, %.1f KB WAV, %.1fs speech",
                    self._engine,
                    elapsed,
                    len(audio_wav) / 1024,
                    len(combined_audio) / sample_rate,
                )
                return SynthesisResult(
                    wav_bytes=audio_wav,
                    duration_sec=elapsed,
                    text_length=len(text),
                    sample_rate=sample_rate,
                )
            logger.error("TTS: Invalid WAV size: %s bytes", len(audio_wav))
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error(
                "TTS: Synthesis exception after %.2fs: %s",
                elapsed,
                exc,
                exc_info=True,
            )

        elapsed = time.perf_counter() - start
        logger.warning("TTS: Returning silence fallback (%.2fs)", elapsed)
        return SynthesisResult(
            wav_bytes=generate_silence_wav(1.0),
            duration_sec=elapsed,
            text_length=len(text),
            sample_rate=16000,
        )
