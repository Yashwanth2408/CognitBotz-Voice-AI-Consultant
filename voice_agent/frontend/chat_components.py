"""
frontend/chat_components.py
----------------------------
Chat bubble renderers, source attribution cards, and latency metric badges.

Design rationale:
  - Styled HTML chat bubbles provide a ChatGPT-quality visual experience.
  - Source cards create transparent, auditable AI responses — users see exactly
    which KB sections informed each answer (spec §20 Feature 7).
  - Latency badges display per-stage timings inline with the response.
  - All components use Streamlit's unsafe_allow_html for rich styling while
    keeping the Python logic clean and readable.
"""

import streamlit as st
from datetime import datetime
from typing import Optional

from memory.history_manager import ChatMessage
from utils.logger import get_logger

logger = get_logger(__name__)

# Colour palette — dark theme aligned with CognitBotz brand
_USER_BUBBLE_BG = "linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%)"
_ASSISTANT_BUBBLE_BG = "linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%)"
_SOURCE_CARD_BG = "rgba(255, 255, 255, 0.04)"
_ACCENT = "#7c83fd"


def render_chat_message(message: ChatMessage) -> None:
    """
    Render a single chat message as a styled bubble.

    User messages appear right-aligned in blue.
    Assistant messages appear left-aligned in dark with the bot icon.

    Args:
        message: ChatMessage dataclass from HistoryManager.
    """
    is_user = message.role == "user"
    avatar = "🎤" if is_user else "🤖"
    bubble_bg = _USER_BUBBLE_BG if is_user else _ASSISTANT_BUBBLE_BG
    align = "flex-end" if is_user else "flex-start"
    text_align = "right" if is_user else "left"
    border_radius = "18px 18px 4px 18px" if is_user else "18px 18px 18px 4px"
    max_width = "75%"

    # Escape any HTML in message content for safety
    safe_content = message.content.replace("<", "&lt;").replace(">", "&gt;")
    # Restore line breaks as HTML
    safe_content = safe_content.replace("\n", "<br>")

    st.markdown(
        f"""
        <div style="
            display: flex;
            justify-content: {align};
            margin: 8px 0;
            animation: fadeInUp 0.3s ease;
        ">
            <div style="
                max-width: {max_width};
                background: {bubble_bg};
                border-radius: {border_radius};
                padding: 12px 16px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.08);
            ">
                <div style="
                    font-size: 11px;
                    color: rgba(255,255,255,0.5);
                    margin-bottom: 4px;
                    text-align: {text_align};
                ">
                    {avatar} {'You' if is_user else 'Aria'} · {message.timestamp}
                </div>
                <div style="
                    color: rgba(255,255,255,0.92);
                    font-size: 14px;
                    line-height: 1.55;
                    text-align: {text_align};
                ">
                    {safe_content}
                </div>
            </div>
        </div>
        <style>
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Render audio player below assistant messages that have audio
    if not is_user and message.audio_bytes:
        col_spacer, col_audio = st.columns([1, 3])
        with col_audio:
            st.audio(message.audio_bytes, format="audio/wav")

    # Render source cards below assistant messages
    if not is_user and message.sources:
        render_source_cards(message.sources)

    # Render latency badge
    if not is_user and message.latency_sec > 0:
        render_latency_badge(message.latency_sec)


def render_source_cards(source_cards: list[dict]) -> None:
    """
    Render knowledge base source attribution cards.

    Displays collapsible source cards showing which KB sections
    were retrieved to generate the response.

    Args:
        source_cards: List of source card dicts from source_formatter.
    """
    if not source_cards:
        return

    with st.expander(f"📚 Sources ({len(source_cards)})", expanded=False):
        for card in source_cards:
            st.markdown(
                f"""
                <div style="
                    background: {_SOURCE_CARD_BG};
                    border: 1px solid rgba(124,131,253,0.2);
                    border-left: 3px solid {_ACCENT};
                    border-radius: 8px;
                    padding: 10px 14px;
                    margin: 6px 0;
                ">
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 4px;
                    ">
                        <span style="
                            font-size: 12px;
                            font-weight: 600;
                            color: {_ACCENT};
                        ">
                            {card['index']}. {card['source']}
                        </span>
                        <span style="
                            font-size: 11px;
                            background: rgba(124,131,253,0.15);
                            color: {_ACCENT};
                            padding: 2px 8px;
                            border-radius: 10px;
                        ">
                            {card['score_pct']} match
                        </span>
                    </div>
                    <div style="
                        font-size: 12px;
                        color: rgba(255,255,255,0.55);
                        line-height: 1.4;
                        font-style: italic;
                    ">
                        {card['preview']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_latency_badge(latency_sec: float) -> None:
    """
    Render a compact latency badge below an assistant response.

    Args:
        latency_sec: Total pipeline response time in seconds.
    """
    colour = "#4caf50" if latency_sec < 3 else "#ff9800" if latency_sec < 6 else "#f44336"

    st.markdown(
        f"""
        <div style="
            display: flex;
            justify-content: flex-start;
            margin: 2px 0 8px 0;
        ">
            <span style="
                font-size: 11px;
                color: {colour};
                background: rgba(255,255,255,0.05);
                padding: 2px 10px;
                border-radius: 10px;
                border: 1px solid {colour}33;
            ">
                ⏱ {latency_sec:.2f}s
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_latency_panel(latency_dict: dict[str, str]) -> None:
    """
    Render the detailed per-stage latency metrics in the right panel.

    Args:
        latency_dict: Dict from LatencyMetrics.as_display_dict().
    """
    st.markdown("#### ⏱ Pipeline Latency")
    for stage, value in latency_dict.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(
                f"<span style='font-size:13px; color:rgba(255,255,255,0.7)'>"
                f"{stage}</span>",
                unsafe_allow_html=True,
            )
        with col2:
            is_total = "Total" in stage
            st.markdown(
                f"<span style='font-size:13px; font-weight:{'700' if is_total else '400'}; "
                f"color:{'#7c83fd' if is_total else 'rgba(255,255,255,0.9)'}'>"
                f"{value}</span>",
                unsafe_allow_html=True,
            )


def render_typing_indicator() -> None:
    """Render an animated typing indicator while the pipeline processes."""
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:8px; margin:8px 0;">
            <span style="font-size:22px">🤖</span>
            <div style="display:flex; gap:4px; align-items:center;">
                <span class="dot"></span>
                <span class="dot" style="animation-delay:0.2s"></span>
                <span class="dot" style="animation-delay:0.4s"></span>
            </div>
        </div>
        <style>
        .dot {
            width: 8px; height: 8px;
            background: #7c83fd;
            border-radius: 50%;
            animation: bounce 0.8s infinite;
        }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); opacity: 0.4; }
            50% { transform: translateY(-6px); opacity: 1; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
