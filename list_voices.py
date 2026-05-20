from voice_agent.config.settings import TTS_ENGINE, TTS_MMS_MODEL_ID, TTS_MODEL_PATH
from voice_agent.audio.text_to_speech import is_tts_configured, ensure_piper_voice_model


def run() -> None:
    print("Offline TTS configuration")
    print(f"Engine: {TTS_ENGINE}")
    if TTS_ENGINE == "mms":
        print(f"MMS model: {TTS_MMS_MODEL_ID}")
        print("Voice: English with Indian female speaker (IndicTTS)")
    else:
        print(f"Piper model: {TTS_MODEL_PATH}")
        print(f"Piper ready: {ensure_piper_voice_model()}")
    print(f"Configured: {is_tts_configured()}")


if __name__ == "__main__":
    run()
