"""
frontend/ui.py
--------------
Main Streamlit UI layout — 3-column enterprise chat interface.

Design rationale:
  - Left panel: session history summary + controls.
  - Centre panel: main chat + voice input (primary interaction zone).
  - Right panel: system status + per-stage latency metrics.
  - CSS is injected once at render time to avoid flash-of-unstyled-content.
  - All pipeline calls are synchronous within Streamlit's execution model.
"""

import streamlit as st
from typing import Optional

from config.settings import APP_TITLE, APP_SUBTITLE, APP_VERSION
from config.constants import (
    SESSION_MEMORY, SESSION_ORCHESTRATOR, SESSION_PROCESSING,
    SESSION_STATUS, SESSION_LAST_LATENCY, SESSION_COMPONENTS_READY,
    STATUS_PROCESSING, STATUS_READY, STATUS_ERROR,
)
from backend.session_manager import initialise_session, get_history, get_orchestrator, reset_session
from frontend.chat_components import (
    render_chat_message,
    render_latency_panel,
    render_typing_indicator,
)
from frontend.audio_components import (
    render_voice_input_widget,
    render_status_indicator,
)
from memory.history_manager import HistoryManager
from backend.orchestrator import PipelineResult
from utils.logger import get_logger

logger = get_logger(__name__)


def inject_global_css() -> None:
    """Inject global CSS for dark theme, typography, and layout."""
    st.markdown(
        """
        <style>
        /* ── Global theme ── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .stApp {
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
        }

        /* ── Remove Streamlit default padding ── */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0 !important;
            max-width: 100% !important;
        }

        /* ── Header ── */
        .app-header {
            background: linear-gradient(90deg, #7c83fd22 0%, transparent 100%);
            border-bottom: 1px solid rgba(124,131,253,0.2);
            padding: 12px 0 10px 0;
            margin-bottom: 0;
        }
        .app-title {
            font-size: 22px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.5px;
        }
        .app-subtitle {
            font-size: 12px;
            color: rgba(124,131,253,0.9);
            font-weight: 400;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }

        /* ── Chat container scroll ── */
        .chat-container {
            max-height: 62vh;
            overflow-y: auto;
            padding: 8px 4px;
            scrollbar-width: thin;
            scrollbar-color: rgba(124,131,253,0.3) transparent;
        }

        /* ── Panel cards ── */
        .panel-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
        }

        /* ── Input area ── */
        .stTextInput > div > div > input {
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(124,131,253,0.3) !important;
            border-radius: 10px !important;
            color: #ffffff !important;
            font-size: 14px !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #7c83fd !important;
            box-shadow: 0 0 0 2px rgba(124,131,253,0.2) !important;
        }

        /* ── Buttons ── */
        .stButton > button {
            background: linear-gradient(135deg, #7c83fd 0%, #5c63e8 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 15px rgba(124,131,253,0.4) !important;
        }

        /* ── Expander ── */
        .streamlit-expanderHeader {
            background: rgba(255,255,255,0.04) !important;
            border-radius: 8px !important;
            font-size: 13px !important;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background: rgba(255,255,255,0.02) !important;
        }

        /* ── Audio recorder ── */
        [data-testid="stAudioInput"] {
            background: rgba(124,131,253,0.08) !important;
            border: 1px solid rgba(124,131,253,0.25) !important;
            border-radius: 12px !important;
        }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(124,131,253,0.3); border-radius: 4px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Render the application header bar."""
    st.markdown(
        f"""
        <div class="app-header">
            <div class="app-title">🤖 {APP_TITLE}</div>
            <div class="app-subtitle">{APP_SUBTITLE} · v{APP_VERSION}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_left_panel(history: HistoryManager) -> None:
    """
    Render the left sidebar panel with conversation summary and controls.

    Args:
        history: Current session HistoryManager.
    """
    st.markdown("### 💬 Session")

    # Session statistics
    msg_count = max(0, history.message_count - 1)  # Exclude welcome message
    turn_count = history.memory.turn_count

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Messages", msg_count)
    with col2:
        st.metric("Memory Turns", turn_count)

    st.divider()

    # New session button
    if st.button("🔄 New Session", use_container_width=True, key="btn_new_session"):
        reset_session()
        st.rerun()

    st.divider()

    # Recent history preview in left panel
    st.markdown("##### Recent Exchanges")
    messages = history.get_chat_messages()
    user_msgs = [m for m in messages if m.role == "user"]

    if not user_msgs:
        st.caption("No conversation yet. Ask a question to get started.")
    else:
        # Show last 5 user queries as clickable-looking items
        for msg in user_msgs[-5:][::-1]:
            truncated = msg.content[:60] + ("..." if len(msg.content) > 60 else "")
            st.markdown(
                f"""
                <div style="
                    padding: 8px 10px;
                    margin: 4px 0;
                    background: rgba(255,255,255,0.04);
                    border-left: 2px solid #7c83fd;
                    border-radius: 0 6px 6px 0;
                    font-size: 12px;
                    color: rgba(255,255,255,0.7);
                    cursor: default;
                ">{msg.timestamp} · {truncated}</div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # About section
    with st.expander("ℹ️ About Aria"):
        st.markdown(
            """
            **Aria** is CognitBotz's Voice AI Consultant powered by:
            - 🎤 Faster Whisper (ASR)
            - 🔍 FAISS + BGE (RAG)
            - 💬 Groq Llama 4 (LLM)
            - 🔊 XTTS-v2 (Voice)

            Aria answers questions grounded exclusively in the CognitBotz knowledge base.
            """
        )


def render_right_panel() -> None:
    """
    Render the right panel with system status and latency metrics.
    """
    st.markdown("### 📊 System Status")

    # Current status indicator
    current_status = st.session_state.get(SESSION_STATUS, STATUS_READY)
    render_status_indicator(current_status)

    st.divider()

    # Latency metrics from last pipeline run
    last_latency = st.session_state.get(SESSION_LAST_LATENCY)
    if last_latency is not None:
        render_latency_panel(last_latency.as_display_dict())
    else:
        st.caption("Latency metrics will appear here after your first interaction.")

    st.divider()

    # Knowledge base info
    st.markdown("#### 📚 Knowledge Base")
    st.markdown(
        """
        <div style="font-size:12px; color:rgba(255,255,255,0.6); line-height:1.7">
        ✅ Company Overview<br>
        ✅ Services (8 modules)<br>
        ✅ Solutions & Industries<br>
        ✅ Case Studies<br>
        ✅ Products<br>
        ✅ Technologies<br>
        ✅ FAQs & Contact
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat_panel(history: HistoryManager) -> None:
    """
    Render the central chat panel with message history and input controls.

    Args:
        history: Current session HistoryManager.
    """
    # Chat message history — scrollable container
    messages = history.get_chat_messages()

    chat_container = st.container()
    with chat_container:
        if not messages:
            st.info("Start by recording a voice question or typing below.")
        for message in messages:
            render_chat_message(message)

    # Show typing indicator while processing
    if st.session_state.get(SESSION_PROCESSING, False):
        render_typing_indicator()

    st.divider()

    # ── Voice Input ──
    render_voice_input_section(history)

    # ── Text Input ──
    render_text_input_section(history)


def render_voice_input_section(history: HistoryManager) -> None:
    """Voice recording section with immediate pipeline trigger."""
    wav_bytes = render_voice_input_widget()

    if wav_bytes and not st.session_state.get(SESSION_PROCESSING, False):
        import hashlib
        audio_hash = hashlib.md5(wav_bytes).hexdigest()
        
        # Verify if this specific audio has already been processed to prevent infinite rerun loops
        if st.session_state.get("last_processed_audio_hash") != audio_hash:
            st.session_state["last_processed_audio_hash"] = audio_hash
            _run_pipeline_audio(wav_bytes, history)


def render_text_input_section(history: HistoryManager) -> None:
    """Typed query input with submit button."""
    with st.form(key="text_input_form", clear_on_submit=True):
        col_input, col_submit = st.columns([5, 1])
        with col_input:
            user_text = st.text_input(
                label="Type your question",
                placeholder="e.g. What AI solutions do you offer for manufacturing?",
                label_visibility="collapsed",
                key="text_query_input",
            )
        with col_submit:
            submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted and user_text and not st.session_state.get(SESSION_PROCESSING, False):
        _run_pipeline_text(user_text.strip(), history)


def _run_pipeline_audio(wav_bytes: bytes, history: HistoryManager) -> None:
    """Execute the full voice pipeline and update session state."""
    st.session_state[SESSION_PROCESSING] = True
    st.session_state[SESSION_STATUS] = STATUS_PROCESSING

    orchestrator = get_orchestrator()
    llm_history = history.get_llm_history()

    with st.spinner("Processing your question..."):
        result: PipelineResult = orchestrator.process_audio(wav_bytes, llm_history)

    _handle_pipeline_result(result, history)


def _run_pipeline_text(text: str, history: HistoryManager) -> None:
    """Execute the text pipeline and update session state."""
    st.session_state[SESSION_PROCESSING] = True
    st.session_state[SESSION_STATUS] = STATUS_PROCESSING

    orchestrator = get_orchestrator()
    llm_history = history.get_llm_history()

    with st.spinner("Processing your question..."):
        result: PipelineResult = orchestrator.process_text(text, llm_history)

    _handle_pipeline_result(result, history)


def _handle_pipeline_result(result: PipelineResult, history: HistoryManager) -> None:
    """
    Commit pipeline results to history and update session state.

    Args:
        result: Completed PipelineResult from orchestrator.
        history: Active HistoryManager to record the exchange.
    """
    st.session_state[SESSION_PROCESSING] = False

    if not result.success and not result.response_text:
        st.session_state[SESSION_STATUS] = STATUS_ERROR
        if result.error_message:
            st.warning(f"⚠️ {result.error_message}")
        st.rerun()
        return

    if result.transcript:
        history.add_user_message(result.transcript)

    total_latency = (
        result.latency.total if result.latency and result.latency.total else 0.0
    )

    history.add_assistant_message(
        content=result.response_text,
        user_query=result.transcript or "",
        sources=result.source_cards,
        latency_sec=total_latency,
        audio_bytes=result.audio_bytes,
    )

    # Store latency for the right panel display
    st.session_state[SESSION_LAST_LATENCY] = result.latency
    st.session_state[SESSION_STATUS] = STATUS_READY

    logger.info(
        f"Pipeline complete: transcript='{result.transcript[:50]}', "
        f"latency={total_latency:.2f}s"
    )

    st.rerun()


def render_full_ui() -> None:
    """
    Render the complete 3-column application UI.

    Called once per Streamlit execution cycle from app.py.
    """
    inject_global_css()
    render_header()

    # Ensure all components are initialised before rendering
    initialise_session()
    history = get_history()

    # Three-column layout per spec §21
    left, centre, right = st.columns([1.8, 4, 1.8])

    with left:
        render_left_panel(history)

    with centre:
        render_chat_panel(history)

    with right:
        render_right_panel()
