"""
llm/response_generator.py
--------------------------
Orchestrates LLM response generation for the Voice AI pipeline.

Design rationale:
  - Encapsulates the full LLM call: prompt building → API call → response cleaning.
  - Returns a structured ResponseResult for consistent downstream handling.
  - Falls back gracefully when retrieval finds nothing relevant.
"""

from dataclasses import dataclass
from typing import Optional

from config.prompts import NO_RESULTS_RESPONSE
from llm.groq_client import GroqClient
from llm.prompt_builder import build_messages
from rag.retrieval import RetrievalResult
from utils.logger import get_logger
from utils.helpers import normalize_text_for_tts

logger = get_logger(__name__)


@dataclass
class ResponseResult:
    """
    Structured output from the LLM response generation stage.

    Carries both the raw text response and the TTS-ready cleaned version.
    """
    raw_text: str          # Original LLM output (may contain markdown)
    spoken_text: str       # Cleaned version for voice synthesis
    used_fallback: bool    # True if no retrieval results were available
    model_used: str        # Which Groq model generated this response


class ResponseGenerator:
    """
    Generates grounded, contextual responses using the Groq API.

    Combines retrieval results, conversation history, and the system prompt
    to produce concise, spoken-language responses for the Voice AI consultant.
    """

    def __init__(self, groq_client: GroqClient) -> None:
        """
        Initialise with a configured GroqClient.

        Args:
            groq_client: Authenticated GroqClient instance.
        """
        self._client = groq_client
        logger.info("ResponseGenerator initialised.")

    def generate(
        self,
        user_query: str,
        retrieval_result: RetrievalResult,
        conversation_history: list[dict],
    ) -> ResponseResult:
        """
        Generate a complete spoken response for the user's query.

        Process:
        1. If retrieval is empty → return the standard no-results fallback.
        2. Build the ChatML message list with context and history.
        3. Call Groq API to generate the response.
        4. Clean the response for TTS synthesis.

        Args:
            user_query: The transcribed user question.
            retrieval_result: Retrieved knowledge base chunks.
            conversation_history: Prior conversation turns.

        Returns:
            ResponseResult with raw and TTS-ready text.
        """
        role_answer = _answer_agent_role_question(user_query)
        if role_answer is not None:
            logger.info("Answered query directly from assistant role guidance.")
            return ResponseResult(
                raw_text=role_answer,
                spoken_text=normalize_text_for_tts(role_answer),
                used_fallback=False,
                model_used="assistant-role",
            )

        memory_answer = _answer_session_memory_question(user_query, conversation_history)
        if memory_answer is not None:
            logger.info("Answered query directly from session memory.")
            return ResponseResult(
                raw_text=memory_answer,
                spoken_text=normalize_text_for_tts(memory_answer),
                used_fallback=False,
                model_used="session-memory",
            )

        # Short-circuit: if no relevant context was retrieved, return the
        # standard polite fallback instead of risking hallucination
        if not retrieval_result.has_results:
            logger.warning(
                f"No retrieval results for query '{user_query[:60]}'. "
                f"Returning no-results fallback."
            )
            return ResponseResult(
                raw_text=NO_RESULTS_RESPONSE,
                spoken_text=NO_RESULTS_RESPONSE,
                used_fallback=True,
                model_used="none",
            )

        # Build the complete prompt message list
        messages = build_messages(
            user_query=user_query,
            retrieval_result=retrieval_result,
            conversation_history=conversation_history,
        )

        logger.info(
            f"Calling Groq API | query='{user_query[:60]}' | "
            f"context_chunks={len(retrieval_result.documents)}"
        )

        # Generate the response via Groq — retry logic is handled inside the client
        raw_response = self._client.complete(messages=messages)

        # Normalise the response for voice synthesis
        spoken_text = normalize_text_for_tts(raw_response)

        logger.info(
            f"Response generated ({len(raw_response)} chars → "
            f"{len(spoken_text)} chars after TTS normalisation)"
        )

        return ResponseResult(
            raw_text=raw_response,
            spoken_text=spoken_text,
            used_fallback=False,
            model_used=self._client._primary_model,
        )


def _answer_agent_role_question(user_query: str) -> Optional[str]:
    """Answer questions about what Aria knows and how she helps customers."""
    query = (user_query or "").lower().strip()
    role_patterns = (
        "do we know everything",
        "do you know everything",
        "know everything about the company",
        "what do you know about the company",
        "are you trained on",
        "what can you answer",
        "what can you help",
        "who are you",
        "what are you",
    )

    if not any(pattern in query for pattern in role_patterns):
        return None

    return (
        "Yes, I can help customers understand CognitBotz based on the company knowledge available to me. "
        "I can clarify services, AI solutions, automation capabilities, industries served, case studies, products, technologies, and contact details. "
        "If something is outside my current knowledge base, I will be transparent and guide you to the CognitBotz team for the exact details. "
        "What would you like to clarify about the company?"
    )


def _answer_session_memory_question(
    user_query: str,
    conversation_history: list[dict],
) -> Optional[str]:
    """Answer simple questions about the current session without RAG."""
    query = (user_query or "").lower().strip()
    memory_phrases = (
        "previous question",
        "last question",
        "what did i ask",
        "what was my question",
        "what have i asked",
        "what were we talking",
        "what did we discuss",
        "remember what i asked",
    )

    if not any(phrase in query for phrase in memory_phrases):
        return None

    user_messages = [
        message.get("content", "").strip()
        for message in conversation_history
        if message.get("role") == "user" and message.get("content", "").strip()
    ]

    if not user_messages:
        return (
            "You have not asked a previous question in this session yet. "
            "Ask me something now, and I will remember it for the rest of our conversation."
        )

    if "what have i asked" in query or "what did we discuss" in query or "what were we talking" in query:
        recent_questions = user_messages[-3:]
        if len(recent_questions) == 1:
            return f"So far, you asked: \"{recent_questions[0]}\"."
        joined = "; ".join(f"\"{question}\"" for question in recent_questions)
        return f"Recently, you asked: {joined}."

    return f"Your previous question was: \"{user_messages[-1]}\"."
