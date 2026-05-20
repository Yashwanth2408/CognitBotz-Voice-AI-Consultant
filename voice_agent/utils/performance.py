"""
utils/performance.py
--------------------
Latency measurement utilities for the Voice AI pipeline.

Design rationale:
  - Every stage of the pipeline (STT, retrieval, LLM, TTS) is measured.
  - A context manager pattern provides clean, exception-safe timing.
  - Results are stored in a structured dict for UI display.
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, Optional

from config.constants import LATENCY_FORMAT
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LatencyMetrics:
    """
    Stores per-stage pipeline latency measurements.

    Populated incrementally as each pipeline stage completes.
    Serialised to a dict for display in the Streamlit UI.
    """
    speech_to_text: Optional[float] = None
    retrieval: Optional[float] = None
    llm_generation: Optional[float] = None
    text_to_speech: Optional[float] = None
    total: Optional[float] = None

    def as_display_dict(self) -> dict[str, str]:
        """
        Format metrics for human-readable UI display.

        Returns:
            Dict mapping stage name to formatted latency string.
        """
        stages = {
            "🎤 Speech-to-Text": self.speech_to_text,
            "🔍 Knowledge Retrieval": self.retrieval,
            "💬 LLM Generation": self.llm_generation,
            "🔊 Voice Synthesis": self.text_to_speech,
            "⏱️ Total Response": self.total,
        }
        return {
            label: LATENCY_FORMAT.format(val) if val is not None else "—"
            for label, val in stages.items()
        }

    def log_summary(self) -> None:
        """Write a structured timing summary to the application log."""
        parts = []
        if self.speech_to_text is not None:
            parts.append(f"STT={self.speech_to_text:.3f}s")
        if self.retrieval is not None:
            parts.append(f"Retrieval={self.retrieval:.3f}s")
        if self.llm_generation is not None:
            parts.append(f"LLM={self.llm_generation:.3f}s")
        if self.text_to_speech is not None:
            parts.append(f"TTS={self.text_to_speech:.3f}s")
        if self.total is not None:
            parts.append(f"Total={self.total:.3f}s")

        logger.info(f"Pipeline latency: {' | '.join(parts)}")


class PipelineTimer:
    """
    Accumulates timing measurements across all pipeline stages.

    Usage:
        timer = PipelineTimer()
        timer.start_total()

        with timer.measure("speech_to_text"):
            transcript = stt.transcribe(audio)

        with timer.measure("retrieval"):
            docs = retriever.retrieve(query)

        timer.stop_total()
        metrics = timer.get_metrics()
    """

    def __init__(self) -> None:
        self._measurements: dict[str, float] = {}
        self._total_start: Optional[float] = None

    def start_total(self) -> None:
        """Start the total elapsed timer. Call before first pipeline stage."""
        self._total_start = time.perf_counter()

    def stop_total(self) -> None:
        """Stop the total elapsed timer. Call after last pipeline stage."""
        if self._total_start is not None:
            self._measurements["total"] = time.perf_counter() - self._total_start

    @contextmanager
    def measure(self, stage: str) -> Generator[None, None, None]:
        """
        Context manager to time a named pipeline stage.

        Args:
            stage: Stage identifier (e.g., "speech_to_text", "retrieval").
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self._measurements[stage] = elapsed
            logger.debug(f"Stage [{stage}] completed in {elapsed:.3f}s")

    def get_metrics(self) -> LatencyMetrics:
        """
        Construct a LatencyMetrics snapshot from accumulated measurements.

        Returns:
            LatencyMetrics dataclass with all measured stage durations.
        """
        metrics = LatencyMetrics(
            speech_to_text=self._measurements.get("speech_to_text"),
            retrieval=self._measurements.get("retrieval"),
            llm_generation=self._measurements.get("llm_generation"),
            text_to_speech=self._measurements.get("text_to_speech"),
            total=self._measurements.get("total"),
        )
        metrics.log_summary()
        return metrics

    def reset(self) -> None:
        """Reset all measurements for reuse in the next pipeline run."""
        self._measurements.clear()
        self._total_start = None
