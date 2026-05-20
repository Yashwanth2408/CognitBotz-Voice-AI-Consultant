"""
utils/validators.py
-------------------
Pre-flight validation functions for critical application dependencies.

Design rationale:
  - Fail fast with actionable error messages rather than cryptic runtime crashes.
  - Validators run at startup to surface configuration issues immediately.
  - Each function returns a ValidationResult to allow composite checks.
"""

import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import (
    GROQ_API_KEY,
    KNOWLEDGE_BASE_PATH,
    FAISS_INDEX_DIR,
    TTS_SPEAKER_WAV,
)
from config.constants import FAISS_INDEX_FILENAME, FAISS_DOCSTORE_FILENAME
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Structured result from a validation check."""
    passed: bool
    component: str
    message: str
    is_blocking: bool = True  # If True, application cannot start without this


@dataclass
class ValidationReport:
    """Aggregated results from all validation checks."""
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def all_blocking_passed(self) -> bool:
        """True only if all blocking checks passed."""
        return all(r.passed for r in self.results if r.is_blocking)

    @property
    def warnings(self) -> list[ValidationResult]:
        """Non-blocking failures (warnings)."""
        return [r for r in self.results if not r.passed and not r.is_blocking]

    @property
    def errors(self) -> list[ValidationResult]:
        """Blocking failures (errors)."""
        return [r for r in self.results if not r.passed and r.is_blocking]

    def add(self, result: ValidationResult) -> None:
        self.results.append(result)
        level = "PASS" if result.passed else ("FAIL" if result.is_blocking else "WARN")
        logger.info(f"Validation [{level}] {result.component}: {result.message}")


def validate_groq_api_key() -> ValidationResult:
    """
    Check that GROQ_API_KEY is set and non-empty.
    A missing key will cause all LLM calls to fail immediately.
    """
    if not GROQ_API_KEY or GROQ_API_KEY.strip() == "":
        return ValidationResult(
            passed=False,
            component="Groq API Key",
            message="GROQ_API_KEY environment variable is not set. "
                    "Add it to your .env file or environment.",
            is_blocking=True,
        )
    # Basic format check — Groq keys start with 'gsk_'
    if not GROQ_API_KEY.startswith("gsk_"):
        return ValidationResult(
            passed=False,
            component="Groq API Key",
            message=f"GROQ_API_KEY appears invalid (expected prefix 'gsk_'). "
                    f"Received prefix: '{GROQ_API_KEY[:4]}'",
            is_blocking=True,
        )
    return ValidationResult(
        passed=True,
        component="Groq API Key",
        message="API key is present and has valid format.",
    )


def validate_knowledge_base() -> ValidationResult:
    """
    Check that knowledge_base_master.md exists in the data directory.
    Without the knowledge base, RAG retrieval cannot function.
    """
    if not KNOWLEDGE_BASE_PATH.exists():
        return ValidationResult(
            passed=False,
            component="Knowledge Base",
            message=f"knowledge_base_master.md not found at: {KNOWLEDGE_BASE_PATH}\n"
                    f"Run: python run_ingestion.py to build the index.",
            is_blocking=True,
        )

    file_size = KNOWLEDGE_BASE_PATH.stat().st_size
    if file_size < 1024:  # Less than 1 KB is suspiciously small
        return ValidationResult(
            passed=False,
            component="Knowledge Base",
            message=f"knowledge_base_master.md is unusually small ({file_size} bytes). "
                    f"The file may be empty or corrupted.",
            is_blocking=True,
        )

    return ValidationResult(
        passed=True,
        component="Knowledge Base",
        message=f"Found {file_size / 1024:.1f} KB knowledge base.",
    )


def validate_faiss_index() -> ValidationResult:
    """
    Check that the FAISS index files exist.
    If missing, the user must run run_ingestion.py before launching.
    """
    index_file = FAISS_INDEX_DIR / FAISS_INDEX_FILENAME
    docstore_file = FAISS_INDEX_DIR / FAISS_DOCSTORE_FILENAME

    if not index_file.exists() or not docstore_file.exists():
        return ValidationResult(
            passed=False,
            component="FAISS Index",
            message=f"FAISS index not found at: {FAISS_INDEX_DIR}\n"
                    f"Run: python run_ingestion.py to build the vector index.",
            is_blocking=True,
        )

    return ValidationResult(
        passed=True,
        component="FAISS Index",
        message=f"FAISS index found at: {FAISS_INDEX_DIR}",
    )


def validate_speaker_reference() -> ValidationResult:
    """
    Check that the TTS speaker reference WAV file exists.
    This is non-blocking — XTTS-v2 uses a default voice if reference is absent,
    but voice quality will be reduced compared to a real Indian female reference.
    """
    wav_path = Path(TTS_SPEAKER_WAV)
    if not wav_path.exists():
        return ValidationResult(
            passed=False,
            component="Speaker Reference WAV",
            message=f"Speaker reference not found at: {wav_path}\n"
                    f"A placeholder silence file will be used. "
                    f"Voice quality may not match the desired Indian female accent. "
                    f"Place a 30–60s Indian English female voice WAV at: {wav_path}",
            is_blocking=False,  # App can run with default XTTS voice
        )

    wav_size = wav_path.stat().st_size
    return ValidationResult(
        passed=True,
        component="Speaker Reference WAV",
        message=f"Speaker reference found ({wav_size / 1024:.1f} KB): {wav_path}",
    )


def validate_network_connectivity() -> ValidationResult:
    """
    Verify network connectivity to Groq API endpoint.
    Non-blocking — app loads but all LLM calls will fail without connectivity.
    """
    try:
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
            ("api.groq.com", 443)
        )
        return ValidationResult(
            passed=True,
            component="Network (Groq API)",
            message="Successfully reached api.groq.com:443",
            is_blocking=False,
        )
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return ValidationResult(
            passed=False,
            component="Network (Groq API)",
            message=f"Cannot reach api.groq.com: {e}. "
                    f"Check your internet connection.",
            is_blocking=False,
        )


def validate_audio_device() -> ValidationResult:
    """
    Check that a microphone input device is available.
    Non-blocking — text input mode still works without a microphone.
    """
    try:
        import sounddevice as sd  # type: ignore
        devices = sd.query_devices()
        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        if not input_devices:
            return ValidationResult(
                passed=False,
                component="Audio Input Device",
                message="No microphone detected. Voice input disabled. "
                        "Text input mode is still available.",
                is_blocking=False,
            )
        return ValidationResult(
            passed=True,
            component="Audio Input Device",
            message=f"Found {len(input_devices)} audio input device(s).",
            is_blocking=False,
        )
    except Exception as e:
        return ValidationResult(
            passed=False,
            component="Audio Input Device",
            message=f"Could not query audio devices: {e}",
            is_blocking=False,
        )


def run_all_validations() -> ValidationReport:
    """
    Execute all validation checks and return a consolidated report.

    Called at application startup before any component is initialised.

    Returns:
        ValidationReport with all results.
    """
    report = ValidationReport()

    report.add(validate_groq_api_key())
    report.add(validate_knowledge_base())
    report.add(validate_faiss_index())
    report.add(validate_speaker_reference())
    report.add(validate_network_connectivity())
    report.add(validate_audio_device())

    logger.info(
        f"Validation complete. "
        f"Blocking errors: {len(report.errors)}, "
        f"Warnings: {len(report.warnings)}"
    )

    return report
