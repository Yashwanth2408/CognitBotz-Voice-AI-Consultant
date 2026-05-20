"""
frontend/audio_components.py
-----------------------------
Streamlit audio input components for voice recording.

Design rationale:
  - Streamlit's native audio_input widget (≥1.31) is used when available.
  - Falls back to st.file_uploader for WAV upload on older Streamlit versions.
  - Status indicators give the user clear feedback during every pipeline stage.
  - The recorded WAV bytes are passed directly to the orchestrator.
"""

import streamlit as st
from typing import Optional

from config.constants import (
    STATUS_LISTENING, STATUS_PROCESSING, STATUS_READY, STATUS_ERROR,
    SESSION_RECORDING, SESSION_PROCESSING, SESSION_STATUS,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def render_voice_input_widget() -> Optional[bytes]:
    """
    Render the voice recording widget and return WAV bytes if audio was captured.

    Uses Streamlit's built-in audio_input component which provides a
    browser-based microphone recording button with waveform display.

    Returns:
        WAV bytes if the user recorded audio, None otherwise.
    """
    st.markdown("#### 🎤 Voice Input")

    wav_bytes: Optional[bytes] = None

    try:
        # st.audio_input is available in Streamlit >= 1.31.0
        audio_value = st.audio_input(
            label="Click to record your question",
            key="voice_recorder",
            help="Hold to record. Release to process.",
        )

        if audio_value is not None:
            wav_bytes = audio_value.read()
            logger.info(f"Audio captured: {len(wav_bytes)} bytes via st.audio_input")

    except AttributeError:
        # Fallback for older Streamlit versions — file upload
        st.caption("⚠️ Upgrade Streamlit for live microphone recording.")
        uploaded = st.file_uploader(
            "Upload a WAV audio file",
            type=["wav"],
            key="wav_uploader",
            help="Upload a pre-recorded WAV file to process.",
        )
        if uploaded is not None:
            wav_bytes = uploaded.read()
            logger.info(f"WAV uploaded: {len(wav_bytes)} bytes via file_uploader")

    return wav_bytes


def render_status_indicator(status: str) -> None:
    """
    Display the current pipeline status as a styled indicator.

    Args:
        status: One of the STATUS_* constants from constants.py.
    """
    colour_map = {
        STATUS_LISTENING: "red",
        STATUS_PROCESSING: "orange",
        STATUS_READY: "green",
        STATUS_ERROR: "red",
    }

    colour = colour_map.get(status, "grey")

    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            margin: 4px 0;
        ">
            <span style="
                width: 10px; height: 10px;
                background: {colour};
                border-radius: 50%;
                display: inline-block;
                {'animation: pulse 1.2s infinite;' if colour == 'red' else ''}
            "></span>
            <span style="font-size: 13px; color: rgba(255,255,255,0.85);">
                {status}
            </span>
        </div>
        <style>
        @keyframes pulse {{
            0% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.5; transform: scale(1.2); }}
            100% {{ opacity: 1; transform: scale(1); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_audio_playback(wav_bytes: bytes, label: str = "▶️ Play Response") -> None:
    """
    Render a Streamlit audio player for the TTS response.

    Args:
        wav_bytes: WAV-formatted audio bytes from XTTS-v2.
        label: Caption shown above the audio player.
    """
    if not wav_bytes:
        return

    st.caption(label)
    st.audio(wav_bytes, format="audio/wav")
