"""
audio/vad.py
------------
Voice Activity Detection using Silero VAD.

Design rationale:
  - Silero VAD selected per spec section 6 for high accuracy and low latency.
  - Frame-level speech detection enables automatic recording stop on silence.
  - Model is cached as a module singleton to avoid repeated torch.hub downloads.
  - 512-sample frames at 16kHz = 32ms per frame — mandated by Silero architecture.
"""

import torch
import numpy as np
from functools import lru_cache
from typing import Optional

from config.settings import AUDIO_SAMPLE_RATE, VAD_THRESHOLD, VAD_SILENCE_DURATION_SEC
from config.constants import VAD_FRAME_SAMPLES, VAD_SILENCE_FRAME_THRESHOLD
from utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_silero_vad():
    """
    Download and cache the Silero VAD model from torch.hub.

    First call downloads the model (~2 MB). Subsequent calls use local cache.
    The model and utilities are cached at the module level via lru_cache.

    Returns:
        Tuple of (model, get_speech_timestamps_fn).
    """
    logger.info("Loading Silero VAD model from torch.hub...")
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
        onnx=False,
        verbose=False,
    )
    logger.info("Silero VAD model loaded successfully.")
    return model, utils


class VoiceActivityDetector:
    """
    Frame-level voice activity detector using Silero VAD.

    Processes audio frames in real-time to detect speech onset and offset.
    Drives the automatic recording stop logic in the recorder module.
    """

    def __init__(
        self,
        sample_rate: int = AUDIO_SAMPLE_RATE,
        threshold: float = VAD_THRESHOLD,
        silence_duration_sec: float = VAD_SILENCE_DURATION_SEC,
    ) -> None:
        """
        Initialise VAD with configurable sensitivity and silence timeout.

        Args:
            sample_rate: Audio sample rate (must be 16000 for Silero VAD).
            threshold: Speech probability threshold [0, 1]. Higher = less sensitive.
            silence_duration_sec: Duration of silence before speech is considered ended.
        """
        if sample_rate != 16000:
            raise ValueError(
                f"Silero VAD requires 16000 Hz sample rate. Got: {sample_rate}"
            )

        self._model, self._utils = _load_silero_vad()
        self._sample_rate = sample_rate
        self._threshold = threshold
        self._silence_frames = int(
            silence_duration_sec * sample_rate / VAD_FRAME_SAMPLES
        )
        self._reset_state()

        logger.info(
            f"VoiceActivityDetector ready "
            f"(threshold={threshold}, silence_frames={self._silence_frames})"
        )

    def _reset_state(self) -> None:
        """Reset per-utterance tracking state between recordings."""
        self._speech_detected: bool = False
        self._consecutive_silence: int = 0
        self._model.reset_states()

    def process_frame(self, frame: np.ndarray) -> dict:
        """
        Run VAD inference on a single 512-sample audio frame.

        Args:
            frame: Float32 numpy array of exactly VAD_FRAME_SAMPLES samples,
                   values normalised to [-1.0, 1.0].

        Returns:
            Dict with keys:
              - "is_speech": bool — True if this frame contains speech
              - "speech_prob": float — raw model probability [0, 1]
              - "should_stop": bool — True if silence timeout has elapsed
        """
        if len(frame) != VAD_FRAME_SAMPLES:
            raise ValueError(
                f"VAD frame must be {VAD_FRAME_SAMPLES} samples. Got {len(frame)}."
            )

        # Convert numpy float32 to PyTorch tensor for Silero inference
        tensor = torch.from_numpy(frame).float()
        speech_prob: float = self._model(tensor, self._sample_rate).item()
        is_speech = speech_prob >= self._threshold

        if is_speech:
            self._speech_detected = True
            self._consecutive_silence = 0
        else:
            self._consecutive_silence += 1

        # Stop condition: speech was detected AND silence persisted long enough
        should_stop = (
            self._speech_detected
            and self._consecutive_silence >= self._silence_frames
        )

        return {
            "is_speech": is_speech,
            "speech_prob": speech_prob,
            "should_stop": should_stop,
        }

    def detect_speech_segments(
        self, audio: np.ndarray
    ) -> list[dict]:
        """
        Detect all speech segments in a pre-recorded audio array.

        Uses the Silero utility function get_speech_timestamps for
        batch processing of complete audio files.

        Args:
            audio: Full float32 audio array at 16kHz.

        Returns:
            List of dicts with "start" and "end" sample indices.
        """
        get_speech_timestamps = self._utils[0]
        tensor = torch.from_numpy(audio).float()
        segments = get_speech_timestamps(
            tensor,
            self._model,
            threshold=self._threshold,
            sampling_rate=self._sample_rate,
        )
        return segments

    def has_speech(self, audio: np.ndarray) -> bool:
        """
        Quick check: does the audio contain any detectable speech?

        Args:
            audio: Float32 audio array at 16kHz.

        Returns:
            True if at least one speech segment detected.
        """
        segments = self.detect_speech_segments(audio)
        return len(segments) > 0

    def reset(self) -> None:
        """Reset VAD state. Call before starting a new recording session."""
        self._reset_state()
        logger.debug("VAD state reset")
