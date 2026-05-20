"""
tests/test_pipeline.py
----------------------
Unit and integration tests for the PipelineOrchestrator using mocks.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.orchestrator import PipelineOrchestrator, PipelineResult
from audio.speech_to_text import TranscriptionResult
from audio.text_to_speech import SynthesisResult
from llm.response_generator import ResponseResult
from rag.retrieval import RetrievalResult
from utils.performance import PipelineTimer, LatencyMetrics


class TestPipelineOrchestrator(unittest.TestCase):

    def setUp(self):
        # Create mock dependencies
        self.mock_retriever = MagicMock()
        self.mock_response_generator = MagicMock()
        self.mock_stt = MagicMock()
        self.mock_tts = MagicMock()

        # Instantiate orchestrator
        self.orchestrator = PipelineOrchestrator(
            retriever=self.mock_retriever,
            response_generator=self.mock_response_generator,
            stt=self.mock_stt,
            tts=self.mock_tts,
        )

    def test_process_text_successful_run(self):
        """Pipeline should correctly coordinate Retrieval, LLM, and TTS for a text query."""
        # 1. Mock Retrieval
        mock_doc = MagicMock()
        mock_doc.page_content = "CognitBotz offers advanced AI."
        mock_doc.metadata = {"display_source": "Overview", "kb_section": "Overview"}
        
        retrieval_res = RetrievalResult(
            documents=[mock_doc],
            scores=[0.9],
            context_text="[Source 1: Overview]\nCognitBotz offers advanced AI.",
            source_labels=["Overview"],
            query="What does CognitBotz offer?",
        )
        self.mock_retriever.retrieve.return_value = retrieval_res

        # 2. Mock LLM Response
        llm_res = ResponseResult(
            raw_text="CognitBotz offers AI solutions.",
            spoken_text="CognitBotz offers AI solutions.",
            used_fallback=False,
            model_used="meta-llama/llama-4-maverick-17b-128e-instruct",
        )
        self.mock_response_generator.generate.return_value = llm_res

        # 3. Mock TTS
        tts_res = SynthesisResult(
            wav_bytes=b"dummy_wav",
            duration_sec=0.5,
            text_length=30,
            sample_rate=22050,
        )
        self.mock_tts.synthesise.return_value = tts_res

        # Execute
        result = self.orchestrator.process_text(
            text_query="What does CognitBotz offer?",
            conversation_history=[],
        )

        # Assertions
        assert result.success is True
        assert result.transcript == "What does CognitBotz offer?"
        assert result.response_text == "CognitBotz offers AI solutions."
        assert result.audio_bytes == b"dummy_wav"
        assert len(result.source_cards) == 1
        assert result.source_cards[0]["source"] == "Overview"
        assert result.source_cards[0]["score_pct"] == "90%"

        # Verify calls
        self.mock_retriever.retrieve.assert_called_once_with("What does CognitBotz offer?")
        self.mock_response_generator.generate.assert_called_once()
        self.mock_tts.synthesise.assert_called_once_with("CognitBotz offers AI solutions.")

    def test_process_audio_successful_run(self):
        """Pipeline should transcribe audio and then process the resulting query."""
        # Mock STT transcription
        transcription_res = TranscriptionResult(
            text="hello world",
            language="en",
            duration_sec=0.2,
            confidence=0.95,
            is_empty=False,
        )
        self.mock_stt.transcribe.return_value = transcription_res

        # Mock downstream RAG, LLM, TTS calls
        self.mock_retriever.retrieve.return_value = RetrievalResult(
            documents=[], scores=[], context_text="", source_labels=[], query="hello world"
        )
        # LLM returns fallback because retriever returned no documents
        self.mock_response_generator.generate.return_value = ResponseResult(
            raw_text="No matches.", spoken_text="No matches.", used_fallback=True, model_used="none"
        )
        self.mock_tts.synthesise.return_value = SynthesisResult(
            wav_bytes=b"wav", duration_sec=0.1, text_length=11, sample_rate=22050
        )

        # Execute
        result = self.orchestrator.process_audio(
            wav_bytes=b"fake_mic_input_wav",
            conversation_history=[],
        )

        # Assertions
        assert result.success is True
        assert result.transcript == "hello world"
        self.mock_stt.transcribe.assert_called_once_with(b"fake_mic_input_wav")

    def test_process_audio_empty_transcription(self):
        """Pipeline should return failure if STT returns an empty transcription."""
        transcription_res = TranscriptionResult(
            text="",
            language="en",
            duration_sec=0.1,
            confidence=0.0,
            is_empty=True,
        )
        self.mock_stt.transcribe.return_value = transcription_res

        # Execute
        result = self.orchestrator.process_audio(
            wav_bytes=b"silence",
            conversation_history=[],
        )

        # Assertions
        assert result.success is False
        assert "No speech detected" in result.error_message
        self.mock_retriever.retrieve.assert_not_called()
        self.mock_response_generator.generate.assert_not_called()
