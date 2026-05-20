"""
llm/prompt_builder.py
---------------------
Assembles the complete ChatML message list for Groq API calls.

Design rationale:
  - Prompt construction is centralised here so changes affect all interactions.
  - The message list follows the ChatML format: system → history → context → user.
  - Retrieved context is injected between history and the current user turn.
  - Conversation history provides the last N turns for contextual follow-ups.
  - Token budget awareness prevents overly long prompts that exceed model limits.
"""

from config.prompts import (
    SYSTEM_PROMPT,
    RAG_CONTEXT_TEMPLATE,
    HISTORY_TURN_TEMPLATE,
    NO_RESULTS_RESPONSE,
)
from config.settings import GROQ_MAX_TOKENS
from rag.retrieval import RetrievalResult
from utils.logger import get_logger

logger = get_logger(__name__)

# Rough token estimate: 1 token ≈ 4 characters (English text)
_CHARS_PER_TOKEN: int = 4

# Reserve tokens for the system prompt and response generation
_SYSTEM_PROMPT_TOKENS: int = len(SYSTEM_PROMPT) // _CHARS_PER_TOKEN
_RESPONSE_BUFFER_TOKENS: int = GROQ_MAX_TOKENS
_MAX_CONTEXT_TOKENS: int = 8000  # Leave headroom in 32k context window


def build_messages(
    user_query: str,
    retrieval_result: RetrievalResult,
    conversation_history: list[dict],
) -> list[dict]:
    """
    Construct the full ChatML message list for the LLM.

    Message order (critical for grounding):
    1. System prompt: Defines assistant identity and behaviour constraints.
    2. Conversation history: Prior turns for contextual understanding.
    3. Context message: Retrieved knowledge base chunks.
    4. User message: Current user query.

    Args:
        user_query: The user's current question or statement.
        retrieval_result: Output from KnowledgeRetriever.retrieve().
        conversation_history: List of prior {"role": ..., "content": ...} dicts.

    Returns:
        ChatML-formatted list of message dicts ready for the Groq API.
    """
    messages: list[dict] = []

    # 1. System prompt — always first, sets behaviour for the entire conversation
    messages.append({
        "role": "system",
        "content": SYSTEM_PROMPT,
    })

    # 2. Conversation history — last N turns for contextual continuity
    if conversation_history:
        # Trim history to fit within token budget
        trimmed_history = _trim_history_to_budget(conversation_history)
        messages.extend(trimmed_history)
        logger.debug(f"Included {len(trimmed_history) // 2} history turns in prompt")

    # 3. Retrieved context — injected as an assistant "system" note before the user turn.
    # Using a "user" role for the context injection (rather than system) because
    # some models respond better when context appears in the conversation flow.
    if retrieval_result.has_results:
        context_content = RAG_CONTEXT_TEMPLATE.format(
            context=retrieval_result.context_text
        )
        messages.append({
            "role": "user",
            "content": context_content,
        })
        messages.append({
            "role": "assistant",
            "content": (
                "Thank you. I have reviewed the relevant knowledge base sections. "
                "I'm ready to answer your question based on this information."
            ),
        })
    else:
        # No relevant context found — prime the model to give the fallback response
        logger.warning("No retrieval results. Priming model with no-context instruction.")
        messages.append({
            "role": "user",
            "content": (
                "No relevant information was found in the knowledge base for this query."
            ),
        })
        messages.append({
            "role": "assistant",
            "content": (
                "Understood. I'll let the user know that specific information "
                "is not available in my knowledge base."
            ),
        })

    # 4. Current user query
    messages.append({
        "role": "user",
        "content": user_query,
    })

    total_chars = sum(len(m["content"]) for m in messages)
    logger.debug(
        f"Prompt assembled: {len(messages)} messages, "
        f"~{total_chars // _CHARS_PER_TOKEN} tokens"
    )

    return messages


def _trim_history_to_budget(history: list[dict]) -> list[dict]:
    """
    Trim conversation history to fit within the context token budget.

    Removes oldest turns first to preserve the most recent context.
    History must maintain paired user/assistant structure.

    Args:
        history: Full conversation history as ChatML message dicts.

    Returns:
        Trimmed history that fits within the token budget.
    """
    available_tokens = (
        _MAX_CONTEXT_TOKENS
        - _SYSTEM_PROMPT_TOKENS
        - _RESPONSE_BUFFER_TOKENS
        - 500  # Safety margin
    )

    # Work backwards from most recent to preserve recency
    trimmed: list[dict] = []
    used_chars = 0

    for message in reversed(history):
        msg_chars = len(message.get("content", ""))
        if used_chars + msg_chars > available_tokens * _CHARS_PER_TOKEN:
            break
        trimmed.insert(0, message)
        used_chars += msg_chars

    if len(trimmed) < len(history):
        logger.debug(
            f"History trimmed from {len(history)} to {len(trimmed)} messages "
            f"for token budget compliance"
        )

    return trimmed
