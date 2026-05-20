"""
audio/text_to_speech.py
-----------------------
Fast neural voice synthesis using Microsoft Edge TTS.

Design rationale:
  - Edge TTS selected for speed (1-2s) and Indian female voice support.
  - Uses cloud-based synthesis with zero GPU overhead.
  - Operates asynchronously with proper thread isolation.
  - Output format: WAV bytes for browser playback.
  - Includes comprehensive error handling and fallback to silence.
"""

import asyncio
import io
import re
import threading
import time
import wave
from dataclasses import dataclass
from typing import Optional

from config.settings import AUDIO_SAMPLE_RATE
from utils.logger import get_logger
from utils.helpers import generate_silence_wav

logger = get_logger(__name__)

# ─────────────────────────────────────────────
# Edge TTS Configuration
# ─────────────────────────────────────────────
EDGE_TTS_VOICE = "hi-IN-SwaraNeural"  # Indian female voice (Valid Edge TTS voice)
EDGE_TTS_RATE = "+15%"  # Speaking rate adjustment (positive values speak faster)
EDGE_TTS_PITCH = "+0Hz"  # Pitch adjustment (0Hz = normal)
EDGE_TTS_VOLUME = "+0%"  # edge-tts expects volume as a percentage, not dB.


@dataclass
class SynthesisResult:
    """Structured output from a TTS synthesis operation."""
    wav_bytes: bytes        # WAV-formatted audio bytes
    duration_sec: float     # Synthesis processing time
    text_length: int        # Characters synthesised
    sample_rate: int        # Output sample rate


def _synthesise_edge_tts_sync(text: str) -> Optional[bytes]:
    """
    Synchronous wrapper for Edge TTS using asyncio in dedicated thread.
    
    This runs in a separate thread to avoid asyncio conflicts with Streamlit.
    
    Args:
        text: Text to synthesise.
        
    Returns:
        Audio bytes (MP3 format from Edge TTS) or None on failure.
    """
    from edge_tts import Communicate
    
    result_container = {'audio': None, 'error': None, 'chunk_count': 0}
    
    async def _async_synthesise():
        try:
            logger.info(f"[Edge TTS] Starting synthesis for text: {text[:80]}")
            logger.info(f"[Edge TTS] Config: voice={EDGE_TTS_VOICE}, rate={EDGE_TTS_RATE}, pitch={EDGE_TTS_PITCH}")
            
            communicate = Communicate(
                text=text,
                voice=EDGE_TTS_VOICE,
                rate=EDGE_TTS_RATE,
                pitch=EDGE_TTS_PITCH,
                volume=EDGE_TTS_VOLUME
            )
            
            # Collect audio chunks
            audio_data = io.BytesIO()
            chunk_count = 0
            
            logger.info(f"[Edge TTS] Starting stream iteration...")
            async for chunk in communicate.stream():
                chunk_type = chunk.get("type", "unknown")
                
                if chunk_type == "audio":
                    chunk_size = len(chunk.get("data", b""))
                    audio_data.write(chunk["data"])
                    chunk_count += 1
                    logger.debug(f"[Edge TTS] Audio chunk {chunk_count}: {chunk_size} bytes")
                elif chunk_type == "bytesreceived":
                    bytes_recv = chunk.get("bytesreceived", 0)
                    logger.debug(f"[Edge TTS] Bytes received: {bytes_recv}")
            
            audio_bytes = audio_data.getvalue()
            result_container['chunk_count'] = chunk_count
            logger.info(f"[Edge TTS] Stream complete - {len(audio_bytes)} bytes from {chunk_count} chunks")
            
            if not audio_bytes or len(audio_bytes) == 0:
                raise ValueError(f"Edge TTS returned zero bytes after {chunk_count} chunks")
            
            result_container['audio'] = audio_bytes
            logger.info(f"[Edge TTS] SUCCESS: {len(audio_bytes)} bytes ready for conversion")
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"[Edge TTS] Async synthesis error: {error_msg}", exc_info=True)
            result_container['error'] = error_msg
    
    def _run_synthesis_loop() -> None:
        loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            logger.info("[Edge TTS] Creating worker event loop...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("[Edge TTS] Running async synthesis in worker thread...")
            loop.run_until_complete(_async_synthesise())
        except Exception as e:
            error_msg = f"Event loop error: {type(e).__name__}: {e}"
            logger.error(f"[Edge TTS] {error_msg}", exc_info=True)
            result_container['error'] = error_msg
        finally:
            if loop is not None:
                try:
                    loop.close()
                    logger.info("[Edge TTS] Worker event loop closed successfully")
                except Exception:
                    logger.debug("[Edge TTS] Event loop close skipped", exc_info=True)

    worker = threading.Thread(
        target=_run_synthesis_loop,
        name="edge-tts-synthesis",
        daemon=True,
    )
    worker.start()
    worker.join()
    
    if result_container['error']:
        logger.error(f"[Edge TTS] FAILED: {result_container['error']}")
        logger.error(f"[Edge TTS] Chunks received before failure: {result_container['chunk_count']}")
        return None
    
    audio_result = result_container['audio']
    if audio_result:
        logger.info(f"[Edge TTS] Returning {len(audio_result)} bytes to caller")
    return audio_result


def _split_into_chunks(text: str, max_chars: int = 300) -> list[str]:
    """
    Split long text into sentence-like chunks for TTS-friendly processing.

    The current Edge TTS path can handle the full response, but keeping this
    helper lets tests and future fallback synthesis paths share one splitter.
    """
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if not sentence:
            continue

        if len(sentence) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            words = sentence.split()
            word_chunk = ""
            for word in words:
                candidate = f"{word_chunk} {word}".strip()
                if len(candidate) <= max_chars:
                    word_chunk = candidate
                else:
                    if word_chunk:
                        chunks.append(word_chunk)
                    word_chunk = word
            if word_chunk:
                chunks.append(word_chunk)
            continue

        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            current = sentence

    if current:
        chunks.append(current.strip())

    return chunks


def _load_tts_model():
    """
    Compatibility hook for older tests that expected an XTTS model loader.

    This project now uses Edge TTS, so there is no local model to load. Importing
    Communicate here still validates that the configured TTS backend is present.
    """
    from edge_tts import Communicate

    return Communicate


def _convert_audio_to_wav(audio_bytes: bytes) -> bytes:
    """
    Convert MP3 audio to WAV format if needed.
    
    Args:
        audio_bytes: Audio data (typically MP3 from Edge TTS).
        
    Returns:
        WAV-formatted audio bytes.
    """
    try:
        # Check if already WAV
        if audio_bytes.startswith(b'RIFF'):
            logger.debug(f"Audio already WAV: {len(audio_bytes)} bytes")
            return audio_bytes
        
        # Check if MP3 (Edge TTS returns MP3)
        is_mp3 = (
            audio_bytes.startswith(b'ID3') or
            (len(audio_bytes) >= 2 and audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0)
        )
        
        if is_mp3:
            logger.info(f"Converting MP3 to WAV: {len(audio_bytes)} bytes")
            try:
                from pydub import AudioSegment
                
                # Load MP3. Edge may return MPEG frames without an ID3 tag, so
                # pass the format explicitly instead of relying on header sniffing.
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
                logger.debug(f"Loaded MP3: {len(audio.get_array_of_samples())} samples, {audio.frame_rate}Hz")
                
                # Export to WAV
                wav_buffer = io.BytesIO()
                audio.export(wav_buffer, format="wav")
                wav_bytes = wav_buffer.getvalue()
                
                logger.info(f"MP3 to WAV conversion: {len(audio_bytes)} to {len(wav_bytes)} bytes")
                return wav_bytes
                
            except ImportError as e:
                logger.error(f"pydub not available: {e}, returning MP3 as-is")
                return audio_bytes
            except Exception as e:
                logger.error(f"MP3 conversion failed: {e}", exc_info=True)
                return audio_bytes
        
        # Unknown format, return as-is
        header_hex = audio_bytes[:8].hex() if len(audio_bytes) >= 8 else audio_bytes.hex()
        logger.warning(f"Unknown audio format (header: {header_hex}), returning as-is")
        return audio_bytes
        
    except Exception as e:
        logger.error(f"Audio conversion error: {e}", exc_info=True)
        return audio_bytes


def _wav_sample_rate(wav_bytes: bytes) -> int:
    """Read a WAV byte stream's sample rate, falling back to app default."""
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            return wav_file.getframerate()
    except wave.Error:
        return AUDIO_SAMPLE_RATE


class TextToSpeech:
    """
    Fast voice synthesis using Microsoft Edge TTS cloud service.
    
    - Supports Indian female voice (hi-IN-SwaraUnniF)
    - Synthesis time: typically 1-3 seconds per request
    - Cloud-based, no GPU required
    - Thread-safe async handling
    """

    def __init__(self) -> None:
        """Initialise TextToSpeech."""
        logger.info(f"TextToSpeech initialised with Edge TTS voice: {EDGE_TTS_VOICE}")

    def synthesise(self, text: str) -> SynthesisResult:
        """
        Synthesise text to WAV audio.

        Args:
            text: Clean text to synthesise (no markdown).

        Returns:
            SynthesisResult with audio bytes and metadata.
        """
        # Handle empty text
        if not text or not text.strip():
            logger.info("TTS: Empty text, returning silence")
            silence = generate_silence_wav(0.5)
            return SynthesisResult(
                wav_bytes=silence,
                duration_sec=0.0,
                text_length=0,
                sample_rate=AUDIO_SAMPLE_RATE,
            )

        start = time.perf_counter()
        logger.info(f"TTS: Starting synthesis for {len(text)} chars")
        
        try:
            # Call Edge TTS sync wrapper
            audio_mp3 = _synthesise_edge_tts_sync(text)
            
            if not audio_mp3:
                logger.error("TTS: Edge TTS returned no audio")
                elapsed = time.perf_counter() - start
                return SynthesisResult(
                    wav_bytes=generate_silence_wav(1.0),
                    duration_sec=elapsed,
                    text_length=len(text),
                    sample_rate=AUDIO_SAMPLE_RATE,
                )
            
            # Convert MP3 to WAV
            audio_wav = _convert_audio_to_wav(audio_mp3)
            
            elapsed = time.perf_counter() - start
            
            # Sanity check
            if audio_wav and len(audio_wav) > 100:
                sample_rate = _wav_sample_rate(audio_wav)
                logger.info(f"TTS: Success in {elapsed:.2f}s, {len(audio_wav)/1024:.1f} KB WAV")
                return SynthesisResult(
                    wav_bytes=audio_wav,
                    duration_sec=elapsed,
                    text_length=len(text),
                    sample_rate=sample_rate,
                )
            else:
                logger.error(f"TTS: Invalid WAV size: {len(audio_wav) if audio_wav else 0} bytes")
                
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error(f"TTS: Synthesis exception after {elapsed:.2f}s: {type(e).__name__}: {e}", exc_info=True)
        
        # Fallback: return silence
        elapsed = time.perf_counter() - start
        logger.warning(f"TTS: Returning silence fallback ({elapsed:.2f}s)")
        return SynthesisResult(
            wav_bytes=generate_silence_wav(1.0),
            duration_sec=elapsed,
            text_length=len(text),
            sample_rate=AUDIO_SAMPLE_RATE,
        )
