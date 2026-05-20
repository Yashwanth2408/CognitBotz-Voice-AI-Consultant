"""
audio/playback.py
-----------------
Audio playback utilities for both local device output and Streamlit embedding.

Design rationale:
  - Non-blocking sounddevice playback keeps the UI responsive during speech.
  - Base64 encoding allows WAV audio to be embedded directly in Streamlit
    HTML via st.audio(), which is the recommended Streamlit audio approach.
  - Both playback modes are supported to handle different deployment scenarios:
    local (sounddevice) and browser-based (Streamlit st.audio).
"""

import base64
import threading
import time
from typing import Optional

import numpy as np

from config.settings import AUDIO_SAMPLE_RATE
from utils.logger import get_logger
from utils.helpers import wav_bytes_to_numpy

logger = get_logger(__name__)


def play_audio_nonblocking(wav_bytes: bytes, sample_rate: Optional[int] = None) -> None:
    """
    Play WAV audio through the system speaker in a background thread.

    Non-blocking design allows the UI to update (e.g., display the response text)
    while the audio is playing, rather than freezing until playback completes.

    Args:
        wav_bytes: WAV-formatted audio bytes.
        sample_rate: Override sample rate. Auto-detected from WAV header if None.
    """
    def _play():
        try:
            import sounddevice as sd  # type: ignore

            audio_array, detected_rate = wav_bytes_to_numpy(wav_bytes)
            play_rate = sample_rate or detected_rate

            logger.debug(
                f"Playing audio: {len(audio_array)} samples @ {play_rate}Hz "
                f"({len(audio_array)/play_rate:.1f}s)"
            )

            sd.play(audio_array, samplerate=play_rate)
            sd.wait()  # Block within the thread until playback finishes
            logger.debug("Audio playback complete")

        except Exception as exc:
            logger.warning(f"Audio playback failed: {exc}")

    thread = threading.Thread(target=_play, daemon=True, name="audio-playback")
    thread.start()


def wav_to_base64(wav_bytes: bytes) -> str:
    """
    Encode WAV bytes as a base64 data URI for Streamlit HTML embedding.

    Streamlit's st.audio() accepts WAV bytes directly, but base64 encoding
    is useful for embedding in custom HTML components or downloading.

    Args:
        wav_bytes: WAV-formatted audio bytes.

    Returns:
        Base64-encoded string of the WAV content.
    """
    return base64.b64encode(wav_bytes).decode("utf-8")


def get_audio_data_uri(wav_bytes: bytes) -> str:
    """
    Produce a complete data URI for embedding audio in an HTML <audio> tag.

    Format: data:audio/wav;base64,<encoded>

    Args:
        wav_bytes: WAV-formatted audio bytes.

    Returns:
        Complete data URI string.
    """
    b64 = wav_to_base64(wav_bytes)
    return f"data:audio/wav;base64,{b64}"


def stop_playback() -> None:
    """
    Stop any currently playing sounddevice audio.

    Called when the user starts a new recording while audio is playing.
    """
    try:
        import sounddevice as sd  # type: ignore
        sd.stop()
        logger.debug("Audio playback stopped")
    except Exception as exc:
        logger.debug(f"Could not stop playback: {exc}")
