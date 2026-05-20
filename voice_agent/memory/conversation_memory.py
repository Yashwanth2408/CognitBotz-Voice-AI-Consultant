"""
memory/conversation_memory.py
------------------------------
Sliding-window conversation memory for contextual follow-up support.

Design rationale:
  - ConversationBufferWindowMemory (k=10) keeps the last 10 turns per spec §16.
  - The window prevents unlimited context growth which would exhaust token budgets.
  - Returns history as a flat ChatML message list for direct prompt injection.
  - Thread-safe per-session design — each session gets its own memory instance.
"""

from dataclasses import dataclass, field
from typing import Optional

from config.settings import MEMORY_MAX_TURNS
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConversationTurn:
    """A single exchange between user and assistant."""
    human: str
    assistant: str


class ConversationMemory:
    """
    Sliding-window conversation buffer storing the last N turns.

    Implements the ConversationBufferWindowMemory pattern from LangChain
    in a lightweight, dependency-minimal form that integrates directly
    with our custom prompt builder's ChatML format.
    """

    def __init__(self, max_turns: Optional[int] = None) -> None:
        """
        Initialise memory with a configurable window size.

        Args:
            max_turns: Maximum number of turns to retain.
                       Defaults to MEMORY_MAX_TURNS from settings (10).
        """
        self._max_turns: int = max_turns or MEMORY_MAX_TURNS
        self._turns: list[ConversationTurn] = []
        logger.debug(f"ConversationMemory initialised (max_turns={self._max_turns})")

    def add_turn(self, human_message: str, assistant_message: str) -> None:
        """
        Add a completed conversation exchange to memory.

        Enforces the sliding window by removing the oldest turn when
        the buffer is full. This ensures token budget compliance.

        Args:
            human_message: What the user said.
            assistant_message: What the assistant responded.
        """
        self._turns.append(
            ConversationTurn(human=human_message, assistant=assistant_message)
        )

        # Slide the window: drop oldest turn if buffer is full
        if len(self._turns) > self._max_turns:
            removed = self._turns.pop(0)
            logger.debug(
                f"Memory window full — evicted oldest turn: "
                f"'{removed.human[:40]}...'"
            )

        logger.debug(
            f"Memory updated: {len(self._turns)}/{self._max_turns} turns stored"
        )

    def get_history_as_messages(self) -> list[dict]:
        """
        Return the full conversation history in ChatML format.

        Used by the prompt builder to inject prior context into the LLM prompt.
        Each turn expands to two ChatML messages: one user, one assistant.

        Returns:
            List of {"role": ..., "content": ...} dicts in chronological order.
        """
        messages: list[dict] = []
        for turn in self._turns:
            messages.append({"role": "user", "content": turn.human})
            messages.append({"role": "assistant", "content": turn.assistant})
        return messages

    def get_turns(self) -> list[ConversationTurn]:
        """
        Return the raw list of ConversationTurn objects.

        Useful for the history display panel in the UI.

        Returns:
            List of ConversationTurn dataclasses (oldest first).
        """
        return list(self._turns)

    def clear(self) -> None:
        """
        Reset the memory buffer.

        Called when the user clicks "New Session" in the UI.
        """
        count = len(self._turns)
        self._turns.clear()
        logger.info(f"Conversation memory cleared ({count} turns removed)")

    @property
    def turn_count(self) -> int:
        """Number of turns currently stored in the buffer."""
        return len(self._turns)

    @property
    def is_empty(self) -> bool:
        """True if no conversation history exists yet."""
        return len(self._turns) == 0
