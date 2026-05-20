"""
audio/noise_reduction.py
------------------------
Environmental noise suppression using RNNoise.

Design rationale:
  - RNNoise selected per spec section 6 for real-time noise suppression.
  - Operates on 480-sample frames at 48kHz — the model's fixed window size.
  - Audio must be resampled 16kHz→48kHz before suppression, then back.
  - Graceful degradation: if rnnoise-python is unavailable (e.g., missing DLL
    on Windows), the module falls through silently with a one-time warning.
    This keeps the application functional even without noise suppression.
"""

import numpy as np
from typing import Optional

from config.constants import RNNOISE_FRAME_SAMPLES, RNNOISE_SAMPLE_RATE
from config.settings import AUDIO_SAMPLE_RATE
from utils.logger import get_logger

logger = get_logger(__name__)

# Flag to track RNNoise availability — set once at import time
_RNNOISE_AVAILABLE: bool = False
_RNNoise = None

try:
    from rnnoise import RNNoise as _RNNoiseLib  # type: ignore
    _RNNoise = _RNNoiseLib
    _RNNOISE_AVAILABLE = True
    logger.info("RNNoise noise suppression: available ✓")
except (ImportError, OSError) as _err:
    logger.warning(
        f"RNNoise not available ({_err}). "
        "Noise suppression disabled — audio will be passed through unchanged. "
        "Install 'rnnoise-python' and ensure the native library is present."
    )


def _resample(audio: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    """
    Resample audio from one sample rate to another using linear interpolation.

    For production use with high-fidelity requirements, replace with
    scipy.signal.resample_poly or librosa.resample. Linear interpolation
    is used here to avoid additional heavy dependencies.

    Args:
        audio: Float32 audio array.
        from_rate: Source sample rate.
        to_rate: Target sample rate.

    Returns:
        Resampled float32 audio array.
    """
    if from_rate == to_rate:
        return audio

    # Calculate output length and create resampled array via linear interp
    original_length = len(audio)
    target_length = int(original_length * to_rate / from_rate)
    original_indices = np.linspace(0, original_length - 1, target_length)
    return np.interp(original_indices, np.arange(original_length), audio).astype(
        np.float32
    )


class NoiseReducer:
    """
    Applies RNNoise noise suppression to microphone audio.

    Handles the sample rate conversion between the application's 16kHz
    processing rate and RNNoise's required 48kHz input rate.

    Falls through gracefully if RNNoise is not installed.
    """

    def __init__(self) -> None:
        self._denoiser = None
        if _RNNOISE_AVAILABLE and _RNNoise is not None:
            try:
                self._denoiser = _RNNoise()
                logger.info("NoiseReducer initialised with RNNoise.")
            except Exception as exc:
                logger.warning(f"RNNoise initialisation failed: {exc}. Disabled.")
        else:
            logger.info("NoiseReducer running in pass-through mode (no RNNoise).")

    @property
    def is_active(self) -> bool:
        """True if RNNoise denoiser is loaded and operational."""
        return self._denoiser is not None

    def reduce_noise(self, audio_16k: np.ndarray) -> np.ndarray:
        """
        Apply noise suppression to 16kHz mono audio.

        Process:
        1. Upsample 16kHz → 48kHz for RNNoise compatibility.
        2. Pad to a multiple of RNNOISE_FRAME_SAMPLES.
        3. Process in 480-sample frames.
        4. Downsample 48kHz → 16kHz to restore original rate.

        Args:
            audio_16k: Float32 audio at 16kHz.

        Returns:
            Noise-suppressed float32 audio at 16kHz.
            If RNNoise is unavailable, returns the input unchanged.
        """
        if not self.is_active:
            return audio_16k

        try:
            # Step 1: Upsample to 48kHz for RNNoise
            audio_48k = _resample(audio_16k, AUDIO_SAMPLE_RATE, RNNOISE_SAMPLE_RATE)

            # Step 2: Pad to frame boundary
            frame_size = RNNOISE_FRAME_SAMPLES
            remainder = len(audio_48k) % frame_size
            if remainder != 0:
                padding = frame_size - remainder
                audio_48k = np.concatenate(
                    [audio_48k, np.zeros(padding, dtype=np.float32)]
                )

            # Step 3: Process in 480-sample frames
            # RNNoise expects int16 PCM values scaled to [-32768, 32767]
            audio_48k_int16 = (audio_48k * 32767).clip(-32768, 32767).astype(np.int16)
            denoised_int16 = np.zeros_like(audio_48k_int16)

            for i in range(0, len(audio_48k_int16), frame_size):
                frame = audio_48k_int16[i : i + frame_size]
                if len(frame) == frame_size:
                    denoised_frame = self._denoiser.process_frame(frame)
                    denoised_int16[i : i + frame_size] = denoised_frame

            # Step 4: Restore to float32 and downsample to 16kHz
            denoised_48k = denoised_int16.astype(np.float32) / 32767.0
            denoised_16k = _resample(denoised_48k, RNNOISE_SAMPLE_RATE, AUDIO_SAMPLE_RATE)

            # Trim to original length (removes padding artefacts)
            denoised_16k = denoised_16k[: len(audio_16k)]

            return denoised_16k

        except Exception as exc:
            logger.warning(
                f"Noise reduction failed ({exc}). Returning original audio."
            )
            return audio_16k
