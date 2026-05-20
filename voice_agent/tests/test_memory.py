"""
tests/test_memory.py
--------------------
Unit tests for sliding-window memory and history managers.
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.conversation_memory import ConversationMemory
from memory.history_manager import HistoryManager, ChatMessage


class TestConversationMemory:

    def test_initial_state_empty(self):
        """Memory should be empty upon creation."""
        mem = ConversationMemory(max_turns=3)
        assert mem.turn_count == 0
        assert mem.is_empty is True
        assert len(mem.get_history_as_messages()) == 0

    def test_adds_turns(self):
        """Adding turns should update memory counts and messages list."""
        mem = ConversationMemory(max_turns=3)
        mem.add_turn("hi", "hello")
        assert mem.turn_count == 1
        assert mem.is_empty is False

        msgs = mem.get_history_as_messages()
        assert len(msgs) == 2
        assert msgs[0] == {"role": "user", "content": "hi"}
        assert msgs[1] == {"role": "assistant", "content": "hello"}

    def test_sliding_window_eviction(self):
        """Memory window should evict the oldest turn when full."""
        mem = ConversationMemory(max_turns=2)
        mem.add_turn("q1", "a1")
        mem.add_turn("q2", "a2")
        assert mem.turn_count == 2

        # Adding 3rd turn should evict the first
        mem.add_turn("q3", "a3")
        assert mem.turn_count == 2

        msgs = mem.get_history_as_messages()
        # History should contain q2->a2 and q3->a3, but not q1->a1
        assert msgs[0]["content"] == "q2"
        assert msgs[1]["content"] == "a2"
        assert msgs[2]["content"] == "q3"
        assert msgs[3]["content"] == "a3"

    def test_clear_wipes_memory(self):
        """Calling clear should restore memory to an empty state."""
        mem = ConversationMemory(max_turns=5)
        mem.add_turn("hello", "hi")
        assert mem.turn_count == 1
        mem.clear()
        assert mem.turn_count == 0
        assert len(mem.get_history_as_messages()) == 0


class TestHistoryManager:

    def test_adds_user_and_assistant_messages(self):
        """HistoryManager should record user and assistant chats and update memory."""
        mgr = HistoryManager(max_turns=3)
        mgr.add_welcome_message("Welcome!")
        assert len(mgr.get_chat_messages()) == 1
        assert mgr.get_chat_messages()[0].role == "assistant"

        mgr.add_user_message("Query")
        assert len(mgr.get_chat_messages()) == 2
        assert mgr.get_chat_messages()[1].role == "user"

        mgr.add_assistant_message(
            content="Answer",
            user_query="Query",
            sources=[{"source": "doc"}],
            latency_sec=1.5,
            audio_bytes=b"wav"
        )
        assert len(mgr.get_chat_messages()) == 3
        
        last_msg = mgr.get_chat_messages()[2]
        assert last_msg.role == "assistant"
        assert last_msg.content == "Answer"
        assert last_msg.latency_sec == 1.5
        assert last_msg.audio_bytes == b"wav"
        assert len(last_msg.sources) == 1

        # Check memory synced
        llm_history = mgr.get_llm_history()
        assert len(llm_history) == 2  # one query, one answer
        assert llm_history[0]["content"] == "Query"
        assert llm_history[1]["content"] == "Answer"

    def test_clear_resets_history(self):
        """Clearing HistoryManager should wipe all message logs and memory."""
        mgr = HistoryManager()
        mgr.add_welcome_message("Hello")
        mgr.add_user_message("Query")
        mgr.clear()
        assert len(mgr.get_chat_messages()) == 0
        assert len(mgr.get_llm_history()) == 0
