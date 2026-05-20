"""
backend/session_manager.py
--------------------------
Streamlit session-scoped component lifecycle management.

Design rationale:
  - Streamlit re-runs the entire script on every interaction.
  - Heavy components (models, indices) must be initialised once and stored
    in st.session_state to avoid reloading on every user action.
  - SessionManager provides typed, lazy initialisation of all components.
  - A single initialisation flag prevents redundant component construction.
"""

import threading
import streamlit as st

from config.settings import MEMORY_MAX_TURNS
from config.constants import (
    SESSION_MESSAGES, SESSION_MEMORY, SESSION_ORCHESTRATOR,
    SESSION_RECORDING, SESSION_PROCESSING, SESSION_STATUS,
    SESSION_LAST_LATENCY, SESSION_COMPONENTS_READY,
)
from config.constants import STATUS_READY
from config.prompts import WELCOME_MESSAGE
from memory.history_manager import HistoryManager
from utils.logger import get_logger
from utils.validators import run_all_validations, ValidationReport

logger = get_logger(__name__)

# Process-wide lock to prevent concurrent model loading across threads
_load_lock = threading.Lock()


def initialise_session() -> None:
    """
    Initialise all Streamlit session state variables on first run.

    Checks the SESSION_COMPONENTS_READY flag to ensure this only
    runs once per browser session, not on every Streamlit rerun.

    Side effects:
        - Loads FAISS index, embedding model, Whisper, XTTS-v2.
        - Populates st.session_state with all application components.
    """
    if st.session_state.get(SESSION_COMPONENTS_READY):
        return  # Already initialised — skip

    with _load_lock:
        # Double-check inside lock to see if another thread finished loading while we waited
        if st.session_state.get(SESSION_COMPONENTS_READY):
            return

        logger.info("Initialising session components...")

        # Run pre-flight validation checks
        report: ValidationReport = run_all_validations()

        if not report.all_blocking_passed:
            error_messages = "\n".join(
                f"❌ {r.component}: {r.message}" for r in report.errors
            )
            st.error(
                f"**Application cannot start due to configuration errors:**\n\n"
                f"{error_messages}"
            )
            st.stop()

        # Display non-blocking warnings in the sidebar
        for warning in report.warnings:
            st.sidebar.warning(f"⚠️ {warning.component}: {warning.message}")

        # Initialise history manager (in-memory, per session)
        history = HistoryManager(max_turns=MEMORY_MAX_TURNS)
        history.add_welcome_message(WELCOME_MESSAGE)
        st.session_state[SESSION_MEMORY] = history

        # Initialise the pipeline orchestrator (loads all ML models)
        with st.spinner("Loading AI models... (first launch may take a few minutes)"):
            orchestrator = _build_orchestrator()
        st.session_state[SESSION_ORCHESTRATOR] = orchestrator

        # UI state variables
        st.session_state[SESSION_RECORDING] = False
        st.session_state[SESSION_PROCESSING] = False
        st.session_state[SESSION_STATUS] = STATUS_READY
        st.session_state[SESSION_LAST_LATENCY] = None

        # Mark initialisation complete
        st.session_state[SESSION_COMPONENTS_READY] = True
        logger.info("Session initialisation complete.")


def _build_orchestrator():
    """
    Construct the PipelineOrchestrator with all loaded components.

    Separated from initialise_session() for testability.

    Returns:
        Configured PipelineOrchestrator instance.
    """
    from backend.orchestrator import PipelineOrchestrator
    from rag.vector_store import load_faiss_index
    from rag.retrieval import KnowledgeRetriever
    from llm.groq_client import GroqClient
    from llm.response_generator import ResponseGenerator
    from audio.speech_to_text import SpeechToText
    from audio.text_to_speech import TextToSpeech

    logger.info("Loading FAISS index...")
    vector_store = load_faiss_index()
    retriever = KnowledgeRetriever(vector_store)

    logger.info("Initialising Groq client...")
    groq_client = GroqClient()
    response_gen = ResponseGenerator(groq_client)

    logger.info("Loading Faster Whisper STT model...")
    stt = SpeechToText()

    logger.info("Loading offline TTS (natural Indian English voice)...")
    tts = TextToSpeech()

    orchestrator = PipelineOrchestrator(
        retriever=retriever,
        response_generator=response_gen,
        stt=stt,
        tts=tts,
    )

    logger.info("All components loaded and orchestrator ready.")
    return orchestrator


def get_history() -> HistoryManager:
    """Retrieve the current session's HistoryManager."""
    return st.session_state[SESSION_MEMORY]


def get_orchestrator():
    """Retrieve the current session's PipelineOrchestrator."""
    return st.session_state[SESSION_ORCHESTRATOR]


def reset_session() -> None:
    """
    Clear the conversation history and reset session state.

    Preserves loaded ML models — only conversation data is cleared.
    """
    if SESSION_MEMORY in st.session_state:
        st.session_state[SESSION_MEMORY].clear()
        # Re-add welcome message after reset
        st.session_state[SESSION_MEMORY].add_welcome_message(WELCOME_MESSAGE)

    st.session_state[SESSION_STATUS] = STATUS_READY
    st.session_state[SESSION_LAST_LATENCY] = None
    logger.info("Session conversation reset by user")
