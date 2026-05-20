"""
backend/orchestrator.py
-----------------------
Central pipeline coordinator for the Voice AI Consultant.

Design rationale:
  - The orchestrator is the single entry point for all pipeline executions.
  - It sequences: STT → Retrieval → LLM → TTS → returns PipelineResult.
  - Timing is measured at each stage via PipelineTimer.
  - Text queries bypass the STT stage for the typed-input flow.
  - All errors are caught and returned as structured PipelineResult failures,
    never propagating as unhandled exceptions to the UI.
"""

from dataclasses import dataclass, field
from typing import Optional

from audio.speech_to_text import SpeechToText, TranscriptionResult
from audio.text_to_speech import TextToSpeech, SynthesisResult
from llm.response_generator import ResponseGenerator, ResponseResult
from rag.retrieval import KnowledgeRetriever, RetrievalResult
from rag.source_formatter import format_sources_for_ui, format_sources_for_log
from utils.logger import get_logger
from utils.performance import PipelineTimer, LatencyMetrics

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """
    Complete structured output from one pipeline execution.

    Contains all data needed for the UI to:
    - Display the user transcript
    - Display the assistant response
    - Show source attribution cards
    - Play audio
    - Display latency metrics
    """
    success: bool
    transcript: str                            # User's speech as text
    response_text: str                         # Assistant's text response
    spoken_text: str                           # TTS-normalised version
    audio_bytes: bytes                         # WAV audio of the response
    audio_sample_rate: int                     # Sample rate of the WAV output
    source_cards: list[dict]                   # Source attribution for UI
    latency: Optional[LatencyMetrics]          # Per-stage timing metrics
    error_message: str = ""                    # Set on failure
    used_fallback: bool = False                # True if no KB context found


class PipelineOrchestrator:
    """
    Coordinates all pipeline stages for the Voice AI Consultant.

    Accepts either raw WAV bytes (voice input) or a text string (typed input)
    and returns a fully populated PipelineResult with response text, audio,
    sources, and timing metrics.
    """

    def __init__(
        self,
        retriever: KnowledgeRetriever,
        response_generator: ResponseGenerator,
        stt: SpeechToText,
        tts: TextToSpeech,
    ) -> None:
        """
        Inject all pipeline components.

        Dependency injection pattern allows each component to be tested
        in isolation and replaced without modifying the orchestrator.

        Args:
            retriever: Configured KnowledgeRetriever with loaded FAISS index.
            response_generator: ResponseGenerator with configured GroqClient.
            stt: SpeechToText with loaded Faster Whisper model.
            tts: TextToSpeech with loaded Piper model.
        """
        self._retriever = retriever
        self._response_gen = response_generator
        self._stt = stt
        self._tts = tts
        logger.info("PipelineOrchestrator ready.")

    def process_audio(
        self,
        wav_bytes: bytes,
        conversation_history: list[dict],
    ) -> PipelineResult:
        """
        Full voice pipeline: WAV → transcript → response → audio.

        Args:
            wav_bytes: Recorded microphone audio as WAV bytes.
            conversation_history: ChatML message list from ConversationMemory.

        Returns:
            PipelineResult with all output data.
        """
        timer = PipelineTimer()
        timer.start_total()

        # Stage 1: Speech-to-Text transcription
        try:
            with timer.measure("speech_to_text"):
                transcription: TranscriptionResult = self._stt.transcribe(wav_bytes)
        except Exception as exc:
            logger.error(f"STT failed: {exc}", exc_info=True)
            return self._error_result(f"Speech recognition failed: {exc}")

        if transcription.is_empty:
            logger.info("No speech detected in audio — skipping pipeline")
            return PipelineResult(
                success=False,
                transcript="",
                response_text="",
                spoken_text="",
                audio_bytes=b"",
                audio_sample_rate=22050,
                source_cards=[],
                latency=None,
                error_message="No speech detected. Please try speaking again.",
            )

        logger.info(f"Transcript: '{transcription.clean_text}'")

        # Route to text pipeline with the transcribed query
        return self._process_query(
            query=transcription.clean_text,
            conversation_history=conversation_history,
            timer=timer,
            transcript=transcription.clean_text,
        )

    def process_text(
        self,
        text_query: str,
        conversation_history: list[dict],
    ) -> PipelineResult:
        """
        Text-only pipeline: typed query → response → audio.

        Bypasses the STT stage for keyboard-based interaction.

        Args:
            text_query: User's typed question.
            conversation_history: ChatML message list from ConversationMemory.

        Returns:
            PipelineResult with all output data.
        """
        if not text_query or not text_query.strip():
            return self._error_result("Query cannot be empty.")

        timer = PipelineTimer()
        timer.start_total()

        return self._process_query(
            query=text_query.strip(),
            conversation_history=conversation_history,
            timer=timer,
            transcript=text_query.strip(),
        )

    def _process_query(
        self,
        query: str,
        conversation_history: list[dict],
        timer: PipelineTimer,
        transcript: str,
    ) -> PipelineResult:
        """
        Shared query processing: Retrieval → LLM → TTS.

        Used by both process_audio() and process_text() after obtaining
        the text query.

        Args:
            query: Text query to process.
            conversation_history: Prior conversation context.
            timer: Active PipelineTimer instance.
            transcript: Original user text (may differ from query after cleaning).

        Returns:
            Fully populated PipelineResult.
        """
        # Stage 2: Knowledge retrieval from FAISS
        try:
            with timer.measure("retrieval"):
                retrieval_result: RetrievalResult = self._retriever.retrieve(query)
            logger.info(
                f"Retrieval: {format_sources_for_log(retrieval_result)}"
            )
        except Exception as exc:
            logger.error(f"Retrieval failed: {exc}", exc_info=True)
            return self._error_result(f"Knowledge retrieval failed: {exc}")

        # Stage 3: LLM response generation via Groq
        try:
            with timer.measure("llm_generation"):
                response_result: ResponseResult = self._response_gen.generate(
                    user_query=query,
                    retrieval_result=retrieval_result,
                    conversation_history=conversation_history,
                )
        except Exception as exc:
            logger.error(f"LLM generation failed: {exc}", exc_info=True)
            return self._error_result(f"Response generation failed: {exc}")

        # Stage 4: Text-to-Speech synthesis via Piper
        try:
            with timer.measure("text_to_speech"):
                synthesis_result: SynthesisResult = self._tts.synthesise(
                    response_result.spoken_text
                )
        except Exception as exc:
            logger.error(f"TTS synthesis failed: {exc}", exc_info=True)
            # TTS failure is non-fatal — return text response without audio
            synthesis_result = SynthesisResult(
                wav_bytes=b"", duration_sec=0.0,
                text_length=len(response_result.spoken_text), sample_rate=22050
            )

        timer.stop_total()
        latency = timer.get_metrics()

        # Format source cards for UI display
        source_cards = format_sources_for_ui(retrieval_result)

        return PipelineResult(
            success=True,
            transcript=transcript,
            response_text=response_result.raw_text,
            spoken_text=response_result.spoken_text,
            audio_bytes=synthesis_result.wav_bytes,
            audio_sample_rate=synthesis_result.sample_rate,
            source_cards=source_cards,
            latency=latency,
            used_fallback=response_result.used_fallback,
        )

    @staticmethod
    def _error_result(message: str) -> PipelineResult:
        """Create a standardised failure PipelineResult."""
        logger.error(f"Pipeline error: {message}")
        return PipelineResult(
            success=False,
            transcript="",
            response_text=f"I encountered an error: {message}",
            spoken_text="",
            audio_bytes=b"",
            audio_sample_rate=22050,
            source_cards=[],
            latency=None,
            error_message=message,
        )
