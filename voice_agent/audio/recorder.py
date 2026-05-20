"""
audio/recorder.py
-----------------
VAD-gated microphone recording using sounddevice.

Design rationale:
  - Recording automatically starts on speech and stops on silence (spec §6).
  - The fixed-duration fallback ensures the UI never gets stuck if VAD fails.
  - Audio is captured as float32 at 16kHz mono — the format Faster Whisper expects.
  - Threaded recording allows the UI to remain responsive during capture.
"""

import io
import queue
import threading
import time
import wave
import numpy as np
from dataclasses import dataclass
from typing import Callable, Optional

from config.settings import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    MAX_RECORDING_DURATION_SEC,
    VAD_THRESHOLD,
)
from config.constants import VAD_FRAME_SAMPLES
from audio.vad import VoiceActivityDetector
from audio.noise_reduction import NoiseReducer
from utils.logger import get_logger
from utils.helpers import numpy_to_wav_bytes

logger = get_logger(__name__)


@dataclass
class RecordingResult:
    """Result from a microphone recording session."""
    audio: np.ndarray          # Float32 audio at 16kHz
    wav_bytes: bytes           # WAV-formatted bytes for Whisper/playback
    duration_sec: float        # Actual recording duration
    was_vad_gated: bool        # True if stopped by VAD silence detection
    has_speech: bool           # True if VAD detected speech in the audio


class AudioRecorder:
    """
    VAD-gated microphone recorder.

    Captures audio from the default microphone, applies Voice Activity Detection
    to automatically stop on silence, then applies noise suppression before
    returning the processed audio for transcription.
    """

    def __init__(
        self,
        sample_rate: int = AUDIO_SAMPLE_RATE,
        max_duration_sec: int = MAX_RECORDING_DURATION_SEC,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Initialise the recorder with VAD and noise reduction.

        Args:
            sample_rate: Capture sample rate (16000 Hz).
            max_duration_sec: Safety cap on recording duration.
            status_callback: Optional function called with status strings
                             so the UI can show live "Listening..." indicators.
        """
        self._sample_rate = sample_rate
        self._max_duration_sec = max_duration_sec
        self._status_callback = status_callback or (lambda s: None)

        self._vad = VoiceActivityDetector(sample_rate=sample_rate)
        self._noise_reducer = NoiseReducer()

        self._audio_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()

        logger.info(
            f"AudioRecorder initialised "
            f"(rate={sample_rate}Hz, max={max_duration_sec}s, "
            f"noise_reduction={'active' if self._noise_reducer.is_active else 'disabled'})"
        )

    def record(self) -> RecordingResult:
        """
        Record audio from the microphone until VAD detects silence.

        Pipeline:
        1. Open sounddevice input stream at 16kHz mono.
        2. Feed 512-sample frames to Silero VAD.
        3. Stop when silence follows speech, or max duration is reached.
        4. Apply RNNoise suppression to the complete recording.
        5. Return WAV bytes ready for Faster Whisper.

        Returns:
            RecordingResult with processed audio and metadata.

        Raises:
            RuntimeError: If no audio input device is available.
        """
        try:
            import sounddevice as sd  # type: ignore
        except ImportError:
            raise RuntimeError(
                "sounddevice is not installed. "
                "Run: pip install sounddevice"
            )

        self._vad.reset()
        self._stop_event.clear()
        frames: list[np.ndarray] = []
        start_time = time.time()

        self._status_callback("🔴 Listening...")
        logger.info("Recording started")

        def _audio_callback(indata: np.ndarray, frame_count: int, time_info, status):
            """sounddevice callback — receives audio frames from the OS."""
            if status:
                logger.debug(f"sounddevice status: {status}")
            # Copy frame to avoid reference issues (indata is a view)
            frames.append(indata[:, 0].copy())
            self._audio_queue.put(indata[:, 0].copy())

        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocksize=VAD_FRAME_SAMPLES,
                callback=_audio_callback,
            ):
                while not self._stop_event.is_set():
                    elapsed = time.time() - start_time

                    # Safety cap — stop at max duration regardless of VAD
                    if elapsed >= self._max_duration_sec:
                        logger.warning(
                            f"Recording capped at {self._max_duration_sec}s max duration"
                        )
                        break

                    # Process VAD on the latest queued frame
                    try:
                        frame = self._audio_queue.get(timeout=0.1)
                        vad_result = self._vad.process_frame(frame)

                        if vad_result["should_stop"]:
                            logger.info(
                                f"VAD silence detected after "
                                f"{elapsed:.1f}s — stopping recording"
                            )
                            break
                    except queue.Empty:
                        continue

        except Exception as exc:
            raise RuntimeError(f"Audio recording failed: {exc}") from exc

        duration = time.time() - start_time
        logger.info(f"Recording stopped: {duration:.2f}s captured")

        # Concatenate all frames into a single audio array
        if not frames:
            logger.warning("No audio frames captured")
            silence = np.zeros(VAD_FRAME_SAMPLES, dtype=np.float32)
            return RecordingResult(
                audio=silence,
                wav_bytes=numpy_to_wav_bytes(silence, self._sample_rate),
                duration_sec=0.0,
                was_vad_gated=False,
                has_speech=False,
            )

        raw_audio = np.concatenate(frames, axis=0)

        # Apply noise suppression — improves Whisper accuracy in noisy environments
        self._status_callback("⚙️ Processing audio...")
        clean_audio = self._noise_reducer.reduce_noise(raw_audio)

        # Quick speech presence check using VAD batch detection
        has_speech = self._vad.has_speech(clean_audio)

        wav_bytes = numpy_to_wav_bytes(clean_audio, self._sample_rate)

        return RecordingResult(
            audio=clean_audio,
            wav_bytes=wav_bytes,
            duration_sec=duration,
            was_vad_gated=True,
            has_speech=has_speech,
        )

    def stop(self) -> None:
        """Signal the recording loop to stop (used for manual stop button)."""
        self._stop_event.set()
        logger.info("Recording stop signal sent")
