"""
config/settings.py
------------------
Centralised application settings loaded from environment variables.
All secrets and configurable parameters live here — never hardcoded elsewhere.

Design rationale:
  - Single place to audit all configuration
  - dotenv support for local development
  - Fails fast if critical vars (e.g., GROQ_API_KEY) are missing
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the project root (voice_agent/ parent).
# In production (Docker, cloud) these vars come from the environment directly.
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)


# ─────────────────────────────────────────────
# Groq LLM Configuration
# ─────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# Primary model per spec section 14 — Llama 3.3 70B on Groq
GROQ_MODEL_PRIMARY: str = os.getenv(
    "GROQ_MODEL_PRIMARY",
    "llama-3.3-70b-versatile"
)
# Fallback model if primary is unavailable
GROQ_MODEL_FALLBACK: str = os.getenv(
    "GROQ_MODEL_FALLBACK",
    "llama-3.1-8b-instant"
)
GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.3"))
GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "1024"))
GROQ_TIMEOUT_SECONDS: int = int(os.getenv("GROQ_TIMEOUT_SECONDS", "30"))
GROQ_MAX_RETRIES: int = int(os.getenv("GROQ_MAX_RETRIES", "3"))


# ─────────────────────────────────────────────
# RAG & Embedding Configuration
# ─────────────────────────────────────────────

# Embedding model — BAAI/bge-small-en-v1.5 per spec section 11
EMBEDDING_MODEL_NAME: str = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "BAAI/bge-small-en-v1.5"
)

# Chunk sizing tuned for the structured markdown knowledge base.
# 500 tokens balances context richness vs retrieval precision.
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

# Number of top documents to retrieve per query
TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "5"))

# Minimum similarity score threshold (0–1 cosine).
# Chunks below this score are excluded to reduce noise.
RETRIEVAL_SCORE_THRESHOLD: float = float(
    os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.3")
)


# ─────────────────────────────────────────────
# Conversation Memory Configuration
# ─────────────────────────────────────────────

# Last 10 turns per spec section 16
MEMORY_MAX_TURNS: int = int(os.getenv("MEMORY_MAX_TURNS", "10"))


# ─────────────────────────────────────────────
# Audio Configuration
# ─────────────────────────────────────────────

# Standard 16kHz mono — required by Silero VAD and Faster Whisper
AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS: int = 1  # Mono only

# Silero VAD sensitivity — 0.5 is the balanced default
VAD_THRESHOLD: float = float(os.getenv("VAD_THRESHOLD", "0.5"))

# Silence duration (seconds) before recording stops automatically
VAD_SILENCE_DURATION_SEC: float = float(
    os.getenv("VAD_SILENCE_DURATION_SEC", "1.5")
)

# Maximum single recording duration (safety cap)
MAX_RECORDING_DURATION_SEC: int = int(
    os.getenv("MAX_RECORDING_DURATION_SEC", "60")
)

# Faster Whisper model size — 'small.en' per spec section 7
WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "small.en")

# Compute type — 'float16' on GPU, 'int8' on CPU for speed
WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")


# ─────────────────────────────────────────────
# TTS (fully offline) Configuration
# ─────────────────────────────────────────────

# Engine: "piper" = natural sentence flow (default), "mms" = Indian female VITS
TTS_ENGINE: str = os.getenv("TTS_ENGINE", "piper").strip().lower()

# MMS VITS — English with Indian female speaker (offline after first download)
TTS_MMS_MODEL_ID: str = os.getenv(
    "TTS_MMS_MODEL_ID",
    "onecxi/mms-english-female-indic",
)

TTS_VOICES_DIR: Path = Path(__file__).parent.parent / "assets" / "voices"

# Piper fallback voice — Indian English (en_IN-spicor-medium)
TTS_MODEL_PATH: str = os.getenv(
    "TTS_MODEL_PATH",
    str(TTS_VOICES_DIR / "en_IN-spicor-medium.onnx"),
)

# Speaking rate for Piper (slightly slower = clearer, more natural)
TTS_LENGTH_SCALE: float = float(os.getenv("TTS_LENGTH_SCALE", "0.98"))

# Pause between sentences when stitching audio (seconds)
TTS_SENTENCE_PAUSE_SEC: float = float(os.getenv("TTS_SENTENCE_PAUSE_SEC", "0.32"))

# Download Piper voice on startup when missing (one-time internet)
TTS_AUTO_DOWNLOAD: bool = os.getenv("TTS_AUTO_DOWNLOAD", "true").lower() in (
    "1",
    "true",
    "yes",
)

# Legacy env names (still honoured for overrides)
if os.getenv("PIPER_MODEL_PATH"):
    TTS_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", TTS_MODEL_PATH)
PIPER_MODEL_PATH: str = TTS_MODEL_PATH
PIPER_BINARY_PATH: str = os.getenv("PIPER_BINARY_PATH", "")
PIPER_CONFIG_PATH: str = f"{TTS_MODEL_PATH}.json"
PIPER_SPEAKER_ID: int = int(os.getenv("PIPER_SPEAKER_ID", "0"))
PIPER_LENGTH_SCALE: float = TTS_LENGTH_SCALE


# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────

BASE_DIR: Path = Path(__file__).parent.parent
DATA_DIR: Path = BASE_DIR / "data"
FAISS_INDEX_DIR: Path = DATA_DIR / "faiss_index"
EMBEDDINGS_CACHE_DIR: Path = DATA_DIR / "embeddings_cache"
KNOWLEDGE_BASE_PATH: Path = DATA_DIR / "knowledge_base_master.md"
ASSETS_DIR: Path = BASE_DIR / "assets"
AUDIO_OUTPUT_DIR: Path = ASSETS_DIR / "audio"
LOGS_DIR: Path = BASE_DIR / "logs"


# ─────────────────────────────────────────────
# Logging Configuration
# ─────────────────────────────────────────────

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10 MB
LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))


# ─────────────────────────────────────────────
# Application Metadata
# ─────────────────────────────────────────────

APP_TITLE: str = "CognitBotz Voice AI Consultant"
APP_SUBTITLE: str = "Enterprise AI Knowledge Assistant"
APP_VERSION: str = "1.0.0"
