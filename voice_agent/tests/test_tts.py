"""
tests/test_tts.py
-----------------
Unit tests for the Text-to-Speech module (Piper).
"""

import sys
import pytest
import asyncio
import io
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTextNormalisation:
    """Test TTS text normalisation without loading the model."""

    def test_removes_markdown_bold(self):
        from utils.helpers import normalize_text_for_tts
        result = normalize_text_for_tts("We offer **AI automation** services.")
        assert "**" not in result
        assert "AI automation" in result

    def test_removes_markdown_headers(self):
        from utils.helpers import normalize_text_for_tts
        result = normalize_text_for_tts("## Services\nWe offer great services.")
        assert "##" not in result
        assert "Services" in result

    def test_removes_bullet_points(self):
        from utils.helpers import normalize_text_for_tts
        text = "Features:\n- Feature one\n- Feature two"
        result = normalize_text_for_tts(text)
        assert "- " not in result

    def test_preserves_sentences(self):
        from utils.helpers import normalize_text_for_tts
        original = "CognitBotz was founded in 2019. We serve global clients."
        result = normalize_text_for_tts(original)
        assert "CognitBotz was founded in 2019" in result
        assert "serve global clients" in result

    def test_expands_ampersand_for_speech(self):
        from utils.helpers import normalize_text_for_tts
        result = normalize_text_for_tts("AI & Automation services")
        assert result == "AI and Automation services."

    def test_bullet_lines_become_sentence_breaks(self):
        from utils.helpers import normalize_text_for_tts
        text = "We offer:\n- AI automation\n- Consulting"
        result = normalize_text_for_tts(text)
        assert "AI automation" in result
        assert "Consulting" in result
        assert "\n" not in result

    def test_truncate_at_sentence_boundary(self):
        from utils.helpers import truncate_text
        text = "First sentence. Second sentence. Third sentence."
        result = truncate_text(text, max_chars=30)
        # Should end at a sentence boundary, not mid-word
        assert result.endswith(".") or result.endswith("...")


class TestSentenceSplitting:
    """Test sentence splitting for natural TTS pacing."""

    def test_short_text_single_sentence(self):
        from audio.text_to_speech import _split_into_sentences
        text = "Hello, I am Aria, your CognitBotz assistant."
        sentences = _split_into_sentences(text)
        assert len(sentences) == 1

    def test_long_text_splits_into_sentences(self):
        from audio.text_to_speech import _split_into_sentences
        text = (
            "CognitBotz provides intelligent automation. "
            "We also offer AI consulting services. "
            "Our team has delivered over 500 projects."
        )
        sentences = _split_into_sentences(text)
        assert len(sentences) == 3

    def test_sentences_preserve_content(self):
        from audio.text_to_speech import _split_into_sentences
        text = "First sentence. Second sentence. Third sentence."
        sentences = _split_into_sentences(text)
        all_text = " ".join(sentences)
        assert "First sentence" in all_text
        assert "Second sentence" in all_text
        assert "Third sentence" in all_text


def _require_tts() -> None:
    from audio.text_to_speech import TextToSpeech
    tts = TextToSpeech()
    if tts._mms is None and tts._piper is None:
        pytest.skip("Offline TTS model is not available for tests.")


class TestTextToSpeech:
    """Integration tests for offline TTS synthesis."""

    @pytest.mark.slow
    def test_tts_model_loads(self):
        """TTS backend should load without error."""
        _require_tts()
        from audio.text_to_speech import TextToSpeech
        tts = TextToSpeech()
        assert tts._mms is not None or tts._piper is not None

    @pytest.mark.slow
    def test_synthesise_short_text_returns_wav(self):
        """Synthesis should return valid WAV bytes."""
        _require_tts()
        from audio.text_to_speech import TextToSpeech
        tts = TextToSpeech()
        result = tts.synthesise("Hello from CognitBotz.")

        assert result.wav_bytes, "Expected non-empty WAV bytes"
        assert result.duration_sec > 0, "Expected positive synthesis duration"

        # Verify output is valid WAV
        buf = io.BytesIO(result.wav_bytes)
        try:
            with wave.open(buf, "rb") as wf:
                assert wf.getnchannels() >= 1
                assert wf.getframerate() > 0
        except wave.Error as exc:
            pytest.fail(f"Output is not valid WAV: {exc}")

    @pytest.mark.slow
    def test_synthesise_empty_text_returns_silence(self):
        """Empty text input should return silence, not crash."""
        _require_tts()
        from audio.text_to_speech import TextToSpeech
        tts = TextToSpeech()
        result = tts.synthesise("")
        assert result is not None
        assert isinstance(result.wav_bytes, bytes)

    @pytest.mark.slow
    def test_synthesise_inside_running_event_loop_returns_wav(self):
        """FastAPI endpoints call TTS while an asyncio loop is already running."""
        _require_tts()
        from audio.text_to_speech import TextToSpeech

        async def run_tts():
            return TextToSpeech().synthesise("Hello from the API voice path.")

        result = asyncio.run(run_tts())

        assert result.wav_bytes.startswith(b"RIFF")
        with wave.open(io.BytesIO(result.wav_bytes), "rb") as wf:
            assert wf.getframerate() > 0
