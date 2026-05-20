"""
tests/test_stt.py
-----------------
Unit tests for the Speech-to-Text module (Faster Whisper).
"""

import sys
import struct
import wave
import io
import pytest
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_test_wav(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate a silent WAV file for STT testing."""
    n_samples = int(duration_sec * sample_rate)
    audio = np.zeros(n_samples, dtype=np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


def _make_sine_wav(
    freq_hz: float = 440.0,
    duration_sec: float = 1.0,
    sample_rate: int = 16000,
    amplitude: float = 0.5,
) -> bytes:
    """Generate a sine-wave WAV (not speech — used to test non-speech handling)."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = (amplitude * np.sin(2 * np.pi * freq_hz * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


class TestSpeechToText:

    def test_model_loads(self):
        """Faster Whisper model should load without error."""
        from audio.speech_to_text import _load_whisper_model
        model = _load_whisper_model()
        assert model is not None

    def test_transcribe_silent_audio_returns_empty(self):
        """Silent audio should produce an empty or near-empty transcript."""
        from audio.speech_to_text import SpeechToText
        stt = SpeechToText()
        wav_bytes = _make_test_wav(duration_sec=1.5)
        result = stt.transcribe(wav_bytes)
        # Silent audio should produce minimal text
        assert result is not None
        assert isinstance(result.text, str)
        assert result.is_empty or len(result.text.strip()) < 10

    def test_transcribe_non_speech_audio(self):
        """Non-speech audio (sine wave) should not crash and may return empty."""
        from audio.speech_to_text import SpeechToText
        stt = SpeechToText()
        wav_bytes = _make_sine_wav()
        result = stt.transcribe(wav_bytes)
        assert result is not None
        assert isinstance(result.text, str)

    def test_transcription_result_has_all_fields(self):
        """TranscriptionResult should have all expected fields."""
        from audio.speech_to_text import SpeechToText, TranscriptionResult
        stt = SpeechToText()
        wav_bytes = _make_test_wav()
        result = stt.transcribe(wav_bytes)
        assert hasattr(result, "text")
        assert hasattr(result, "language")
        assert hasattr(result, "duration_sec")
        assert hasattr(result, "confidence")
        assert hasattr(result, "is_empty")

    def test_transcribe_numpy_input(self):
        """SpeechToText should accept numpy arrays as well as WAV bytes."""
        from audio.speech_to_text import SpeechToText
        stt = SpeechToText()
        silence = np.zeros(16000, dtype=np.float32)
        result = stt.transcribe(silence, sample_rate=16000)
        assert result is not None

    def test_empty_bytes_returns_empty_result(self):
        """Empty bytes should return a graceful empty TranscriptionResult."""
        from audio.speech_to_text import SpeechToText
        stt = SpeechToText()
        result = stt.transcribe(b"")
        assert result.is_empty is True
        assert result.text == ""
