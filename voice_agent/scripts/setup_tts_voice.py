"""
Pre-download offline TTS models (MMS + optional Piper fallback).

Run once with internet:
    python voice_agent/scripts/setup_tts_voice.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from audio.text_to_speech import TextToSpeech, is_tts_configured  # noqa: E402
from config.settings import TTS_ENGINE, TTS_MMS_MODEL_ID  # noqa: E402


def main() -> None:
    print(f"Setting up offline TTS (engine={TTS_ENGINE})...")
    if TTS_ENGINE == "mms":
        print(f"Downloading MMS model: {TTS_MMS_MODEL_ID}")
    tts = TextToSpeech()
    result = tts.synthesise("Offline voice setup complete.")
    if result.wav_bytes and len(result.wav_bytes) > 1000:
        print(f"Ready: {len(result.wav_bytes)} bytes test WAV, sr={result.sample_rate}")
        return
    if not is_tts_configured():
        print("Setup failed.")
        raise SystemExit(1)
    print("Configured.")


if __name__ == "__main__":
    main()
