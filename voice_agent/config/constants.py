"""
config/constants.py
-------------------
Named constants for the entire application.

Design rationale:
  - Magic numbers and strings eliminated from production code.
  - Constants grouped by domain for easy navigation.
  - All values here are fixed design decisions, not user-configurable.
"""

# ─────────────────────────────────────────────
# Audio Processing Constants
# ─────────────────────────────────────────────

# Silero VAD processes audio in 512-sample frames at 16kHz = 32ms per frame.
# This frame size is mandated by the Silero VAD model architecture.
VAD_FRAME_SAMPLES: int = 512

# Number of consecutive silent frames before speech is considered ended.
# At 32ms per frame, 48 frames = ~1.5 seconds of silence.
VAD_SILENCE_FRAME_THRESHOLD: int = 48

# RNNoise operates on 480-sample frames at 48kHz.
# Audio must be resampled before applying noise reduction.
RNNOISE_FRAME_SAMPLES: int = 480
RNNOISE_SAMPLE_RATE: int = 48_000

# PCM audio format for all internal processing
AUDIO_DTYPE: str = "float32"

# WAV file bit depth for output files
WAV_SAMPLE_WIDTH: int = 2  # 16-bit PCM


# ─────────────────────────────────────────────
# Embedding Constants
# ─────────────────────────────────────────────

# BGE-small-en-v1.5 produces 384-dimensional vectors.
# This is fixed by the model architecture — do not change.
BGE_EMBEDDING_DIM: int = 384

# BGE models require a query prefix for retrieval tasks.
# This is part of the BGE model's training protocol.
BGE_QUERY_PREFIX: str = "Represent this sentence for searching relevant passages: "

# FAISS index type — flat L2 is exact search (no approximation).
# Suitable for our knowledge base size (~200–500 chunks).
FAISS_INDEX_TYPE: str = "IndexFlatL2"

# File names inside the FAISS index directory
FAISS_INDEX_FILENAME: str = "index.faiss"
FAISS_DOCSTORE_FILENAME: str = "index.pkl"


# ─────────────────────────────────────────────
# UI Constants
# ─────────────────────────────────────────────

# Maximum number of messages shown in the left history panel
MAX_HISTORY_DISPLAY: int = 50

# Avatar labels for chat bubbles
USER_AVATAR: str = "🎤"
ASSISTANT_AVATAR: str = "🤖"

# Latency display format
LATENCY_FORMAT: str = "{:.2f}s"

# Status indicator strings
STATUS_LISTENING: str = "🔴 Listening..."
STATUS_PROCESSING: str = "⚙️ Processing..."
STATUS_RETRIEVING: str = "🔍 Retrieving context..."
STATUS_GENERATING: str = "💬 Generating response..."
STATUS_SPEAKING: str = "🔊 Speaking..."
STATUS_READY: str = "✅ Ready"
STATUS_ERROR: str = "❌ Error"


# ─────────────────────────────────────────────
# Session State Keys
# ─────────────────────────────────────────────
# Centralised keys prevent typo-based bugs across frontend files.

SESSION_MESSAGES: str = "messages"
SESSION_MEMORY: str = "memory"
SESSION_ORCHESTRATOR: str = "orchestrator"
SESSION_RECORDING: str = "is_recording"
SESSION_PROCESSING: str = "is_processing"
SESSION_STATUS: str = "current_status"
SESSION_LAST_LATENCY: str = "last_latency"
SESSION_COMPONENTS_READY: str = "components_ready"


# ─────────────────────────────────────────────
# Pipeline Timing Labels
# ─────────────────────────────────────────────

TIMER_STT: str = "speech_to_text"
TIMER_RETRIEVAL: str = "retrieval"
TIMER_LLM: str = "llm_generation"
TIMER_TTS: str = "text_to_speech"
TIMER_TOTAL: str = "total"


# ─────────────────────────────────────────────
# Retry / Timeout Constants
# ─────────────────────────────────────────────

RETRY_BASE_DELAY_SEC: float = 1.0     # Initial wait before first retry
RETRY_BACKOFF_FACTOR: float = 2.0     # Exponential backoff multiplier
HTTP_CONNECT_TIMEOUT: int = 10        # Seconds to establish connection
HTTP_READ_TIMEOUT: int = 30           # Seconds to wait for response


# ─────────────────────────────────────────────
# Markdown Section Identifiers
# ─────────────────────────────────────────────
# Top-level sections in knowledge_base_master.md.
# Used by the chunker to assign section metadata to chunks.

KB_SECTIONS: list[str] = [
    "COMPANY OVERVIEW",
    "SERVICES",
    "SOLUTIONS",
    "INDUSTRIES",
    "CASE STUDIES",
    "PRODUCTS",
    "TECHNOLOGIES",
    "BLOGS AND INSIGHTS",
    "FAQ",
    "CONTACT INFORMATION",
]
