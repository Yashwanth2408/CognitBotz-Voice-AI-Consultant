"""
memory/history_manager.py
--------------------------
Session-scoped history manager bridging ConversationMemory with the UI.

Design rationale:
  - The UI needs both the raw ConversationMemory (for LLM prompts) and a
    richer chat message list (for display with metadata like timestamps).
  - HistoryManager maintains both in sync without duplication.
  - A single source of truth prevents the UI and LLM from seeing different history.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from memory.conversation_memory import ConversationMemory
from utils.logger import get_logger

logger = get_logger(__name__)

MessageRole = Literal["user", "assistant", "system"]


@dataclass
class ChatMessage:
    """
    Enriched chat message for UI display.

    Extends the basic role/content pair with display metadata
    (timestamp, source attribution, latency).
    """
    role: MessageRole
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    sources: list[dict] = field(default_factory=list)   # Source cards from retrieval
    latency_sec: float = 0.0                             # Total pipeline latency
    audio_bytes: bytes = b""                             # WAV bytes for playback


class HistoryManager:
    """
    Manages the dual-layer conversation history.

    Layer 1 — ConversationMemory: sliding window of (human, assistant) turns
              used for LLM prompt construction.

    Layer 2 — chat_messages: full UI-display-ready list of ChatMessage objects
              including system messages, timestamps, and source metadata.
    """

    def __init__(self, max_turns: int = 10) -> None:
        self._memory = ConversationMemory(max_turns=max_turns)
        self._chat_messages: list[ChatMessage] = []
        logger.debug("HistoryManager initialised")

    def add_welcome_message(self, content: str) -> None:
        """
        Add the initial welcome/system message shown at session start.

        Does not affect the ConversationMemory (system messages are not
        part of the LLM history).

        Args:
            content: Welcome message text.
        """
        self._chat_messages.append(
            ChatMessage(role="assistant", content=content)
        )

    def add_user_message(self, content: str) -> None:
        """
        Record a user message for display immediately after transcription.

        The corresponding assistant message is added later via add_assistant_message().

        Args:
            content: Transcribed user speech.
        """
        self._chat_messages.append(ChatMessage(role="user", content=content))
        logger.debug(f"User message recorded: '{content[:60]}...'")

    def add_assistant_message(
        self,
        content: str,
        user_query: str,
        sources: list[dict] | None = None,
        latency_sec: float = 0.0,
        audio_bytes: bytes = b"",
    ) -> None:
        """
        Record the assistant's response and update the conversation memory.

        This is the point where the exchange is committed to ConversationMemory
        for future LLM context inclusion.

        Args:
            content: Assistant's response text.
            user_query: The user's query that triggered this response.
            sources: List of source card dicts from source_formatter.
            latency_sec: Total pipeline latency for this response.
            audio_bytes: WAV audio for playback in the UI.
        """
        msg = ChatMessage(
            role="assistant",
            content=content,
            sources=sources or [],
            latency_sec=latency_sec,
            audio_bytes=audio_bytes,
        )
        self._chat_messages.append(msg)

        # Commit exchange to the sliding memory window for LLM context
        self._memory.add_turn(
            human_message=user_query,
            assistant_message=content,
        )

        logger.debug(
            f"Assistant message recorded. Memory: {self._memory.turn_count} turns. "
            f"Latency: {latency_sec:.2f}s"
        )

    def get_llm_history(self) -> list[dict]:
        """
        Return conversation history formatted for LLM prompt injection.

        Returns:
            ChatML message list from ConversationMemory.
        """
        return self._memory.get_history_as_messages()

    def get_chat_messages(self) -> list[ChatMessage]:
        """
        Return the full chat message list for UI rendering.

        Returns:
            List of ChatMessage objects in chronological order.
        """
        return list(self._chat_messages)

    def clear(self) -> None:
        """
        Reset both the memory buffer and the UI message list.

        Called when the user starts a new session.
        """
        self._memory.clear()
        self._chat_messages.clear()
        logger.info("History cleared — new session started")

    @property
    def message_count(self) -> int:
        """Total number of UI messages (including system/welcome)."""
        return len(self._chat_messages)

    @property
    def memory(self) -> ConversationMemory:
        """Direct access to the underlying ConversationMemory instance."""
        return self._memory
