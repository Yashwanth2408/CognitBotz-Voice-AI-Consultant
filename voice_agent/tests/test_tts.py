"""
tests/test_tts.py
-----------------
Unit tests for the Text-to-Speech module (XTTS-v2).
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
        assert result == "AI and Automation services"

    def test_truncate_at_sentence_boundary(self):
        from utils.helpers import truncate_text
        text = "First sentence. Second sentence. Third sentence."
        result = truncate_text(text, max_chars=30)
        # Should end at a sentence boundary, not mid-word
        assert result.endswith(".") or result.endswith("...")


class TestChunkSplitting:
    """Test the sentence-chunking logic without loading XTTS-v2."""

    def test_short_text_stays_single_chunk(self):
        from audio.text_to_speech import _split_into_chunks
        text = "Hello, I am Aria, your CognitBotz assistant."
        chunks = _split_into_chunks(text, max_chars=300)
        assert len(chunks) == 1
        assert text in chunks[0]

    def test_long_text_splits_into_multiple_chunks(self):
        from audio.text_to_speech import _split_into_chunks
        # Create a text clearly exceeding 250 chars
        text = (
            "CognitBotz provides intelligent automation. "
            "We also offer AI consulting services. "
            "Our team has delivered over 500 projects. "
            "We operate in five countries globally. "
            "Our CTO is a five-time UiPath MVP."
        )
        chunks = _split_into_chunks(text, max_chars=80)
        assert len(chunks) > 1, "Long text should be split into multiple chunks"

    def test_chunks_preserve_content(self):
        from audio.text_to_speech import _split_into_chunks
        text = "First sentence. Second sentence. Third sentence."
        chunks = _split_into_chunks(text, max_chars=25)
        all_text = " ".join(chunks)
        # All original content should be present
        assert "First sentence" in all_text
        assert "Second sentence" in all_text
        assert "Third sentence" in all_text


class TestTextToSpeech:
    """Integration tests for XTTS-v2 synthesis."""

    @pytest.mark.slow
    def test_tts_model_loads(self):
        """XTTS-v2 model should load without error."""
        from audio.text_to_speech import _load_tts_model
        model = _load_tts_model()
        assert model is not None

    @pytest.mark.slow
    def test_synthesise_short_text_returns_wav(self):
        """Synthesis should return valid WAV bytes."""
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
        from audio.text_to_speech import TextToSpeech
        tts = TextToSpeech()
        result = tts.synthesise("")
        assert result is not None
        assert isinstance(result.wav_bytes, bytes)

    @pytest.mark.slow
    def test_synthesise_inside_running_event_loop_returns_wav(self):
        """FastAPI endpoints call TTS while an asyncio loop is already running."""
        from audio.text_to_speech import TextToSpeech

        async def run_tts():
            return TextToSpeech().synthesise("Hello from the API voice path.")

        result = asyncio.run(run_tts())

        assert result.wav_bytes.startswith(b"RIFF")
        with wave.open(io.BytesIO(result.wav_bytes), "rb") as wf:
            assert wf.getframerate() > 0
