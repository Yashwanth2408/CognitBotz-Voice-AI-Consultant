"""
api/server.py
--------------
FastAPI server wrapper for the Voice AI Consultant backend.

Exposes the orchestrator and session components as REST API endpoints.
Allows the modern frontend to communicate with the backend.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import io
import sys
from pathlib import Path

# Add parent directory to path
_current_dir = Path(__file__).parent.parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from backend.orchestrator import PipelineOrchestrator, PipelineResult
from rag.vector_store import load_faiss_index
from rag.retrieval import KnowledgeRetriever
from llm.groq_client import GroqClient
from llm.response_generator import ResponseGenerator
from audio.speech_to_text import SpeechToText
from audio.text_to_speech import TextToSpeech
from memory.history_manager import HistoryManager
from utils.logger import get_logger
from config.settings import MEMORY_MAX_TURNS
from config.prompts import WELCOME_MESSAGE

logger = get_logger("api")

# Initialize FastAPI app
app = FastAPI(
    title="CognitBotz Voice AI API",
    description="REST API for Voice AI Consultant Backend",
    version="1.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components (initialized once at startup)
_orchestrator: PipelineOrchestrator = None
_stt: SpeechToText = None
_history: HistoryManager = None


@app.on_event("startup")
async def startup_event():
    """Initialize backend components on server startup."""
    global _orchestrator, _stt, _history
    
    logger.info("Initializing API server...")
    
    try:
        # Load FAISS index and components
        logger.info("Loading FAISS index...")
        vector_store = load_faiss_index()
        retriever = KnowledgeRetriever(vector_store)

        logger.info("Initializing Groq client...")
        groq_client = GroqClient()
        response_gen = ResponseGenerator(groq_client)

        logger.info("Loading Faster Whisper STT model...")
        _stt = SpeechToText()

        logger.info("Loading XTTS-v2 TTS model...")
        tts = TextToSpeech()

        # Initialize orchestrator
        _orchestrator = PipelineOrchestrator(
            retriever=retriever,
            response_generator=response_gen,
            stt=_stt,
            tts=tts,
        )
        logger.info("Orchestrator initialized")
        
        # Initialize history manager
        _history = HistoryManager(max_turns=MEMORY_MAX_TURNS)
        _history.add_welcome_message(WELCOME_MESSAGE)
        logger.info("History manager initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize API server: {e}", exc_info=True)
        raise


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "CognitBotz Voice AI API"
    }


@app.post("/api/chat/text")
async def chat_with_text(query: dict):
    """
    Process a text query through the pipeline.
    
    Args:
        query: {"text": "user's question"}
    
    Returns:
        Complete pipeline result with response, audio, and latency.
    """
    try:
        text = query.get("text", "").strip()
        
        if not text:
            raise HTTPException(status_code=400, detail="Text query cannot be empty")
        
        logger.info(f"Processing text query: {text[:50]}...")
        
        # Get conversation history for context
        history_for_context = _history.get_llm_history()
        
        # Process through orchestrator
        result: PipelineResult = _orchestrator.process_text(text, history_for_context)
        
        if not result.success:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result.error_message
                }
            )
        
        # Add to history
        _history.add_user_message(text)
        _history.add_assistant_message(
            content=result.response_text,
            user_query=text,
            sources=result.source_cards,
            latency_sec=result.latency.total if result.latency and result.latency.total else 0.0,
            audio_bytes=result.audio_bytes
        )
        
        # Return result as JSON
        return {
            "success": True,
            "transcript": result.transcript,
            "response_text": result.response_text,
            "audio_bytes_b64": _bytes_to_base64(result.audio_bytes),
            "audio_sample_rate": result.audio_sample_rate,
            "source_cards": result.source_cards,
            "latency": {
                "stt_ms": int(result.latency.speech_to_text * 1000) if result.latency and result.latency.speech_to_text else 0,
                "retrieval_ms": int(result.latency.retrieval * 1000) if result.latency and result.latency.retrieval else 0,
                "llm_ms": int(result.latency.llm_generation * 1000) if result.latency and result.latency.llm_generation else 0,
                "tts_ms": int(result.latency.text_to_speech * 1000) if result.latency and result.latency.text_to_speech else 0,
                "total_ms": int(result.latency.total * 1000) if result.latency and result.latency.total else 0,
            }
        }
        
    except Exception as e:
        logger.error(f"Chat text processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/audio")
async def chat_with_audio(audio_file: UploadFile = File(...)):
    """
    Process audio query through the pipeline.
    
    Args:
        audio_file: Audio file (WAV format preferred)
    
    Returns:
        Complete pipeline result with response, audio, and latency.
    """
    try:
        logger.info(f"Processing audio query: {audio_file.filename}")
        
        # Read audio bytes
        audio_bytes = await audio_file.read()
        
        if not audio_bytes or len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty")
        
        # Get conversation history for context
        history_for_context = _history.get_llm_history()
        
        # Process through orchestrator
        result: PipelineResult = _orchestrator.process_audio(audio_bytes, history_for_context)
        
        if not result.success:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result.error_message
                }
            )
        
        # Add to history
        _history.add_user_message(result.transcript)
        _history.add_assistant_message(
            content=result.response_text,
            user_query=result.transcript,
            sources=result.source_cards,
            latency_sec=result.latency.total if result.latency and result.latency.total else 0.0,
            audio_bytes=result.audio_bytes
        )
        
        # Return result as JSON
        return {
            "success": True,
            "transcript": result.transcript,
            "response_text": result.response_text,
            "audio_bytes_b64": _bytes_to_base64(result.audio_bytes),
            "audio_sample_rate": result.audio_sample_rate,
            "source_cards": result.source_cards,
            "latency": {
                "stt_ms": int(result.latency.speech_to_text * 1000) if result.latency and result.latency.speech_to_text else 0,
                "retrieval_ms": int(result.latency.retrieval * 1000) if result.latency and result.latency.retrieval else 0,
                "llm_ms": int(result.latency.llm_generation * 1000) if result.latency and result.latency.llm_generation else 0,
                "tts_ms": int(result.latency.text_to_speech * 1000) if result.latency and result.latency.text_to_speech else 0,
                "total_ms": int(result.latency.total * 1000) if result.latency and result.latency.total else 0,
            }
        }
        
    except Exception as e:
        logger.error(f"Chat audio processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history():
    """Get conversation history."""
    try:
        messages = _history.get_chat_messages()
        return {
            "success": True,
            "messages": [
                {
                    "role": msg.role,
                    "text": msg.content,
                    "audio_bytes_b64": _bytes_to_base64(msg.audio_bytes) if msg.audio_bytes else None,
                    "timestamp": msg.timestamp
                }
                for msg in messages
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/history/clear")
async def clear_history():
    """Clear conversation history."""
    try:
        _history.clear()
        _history.add_welcome_message(WELCOME_MESSAGE)
        return {
            "success": True,
            "message": "History cleared"
        }
    except Exception as e:
        logger.error(f"Failed to clear history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _bytes_to_base64(data: bytes) -> str:
    """Convert bytes to base64 string for JSON transfer."""
    import base64
    if not data:
        return ""
    return base64.b64encode(data).decode('utf-8')


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
