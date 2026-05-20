"""
llm/groq_client.py
------------------
Groq API client wrapper with retry logic, timeout handling, and error management.

Design rationale:
  - Groq is the only cloud-based component per spec section 14.
  - API key loaded exclusively from environment — never hardcoded.
  - Exponential backoff retry handles transient API failures gracefully.
  - Streaming support enables faster perceived response time in the UI.
  - The client is instantiated once and reused across all LLM calls.
"""

import time
from typing import Generator, Optional

from groq import Groq, APIConnectionError, APIStatusError, RateLimitError

from config.settings import (
    GROQ_API_KEY,
    GROQ_MODEL_PRIMARY,
    GROQ_MODEL_FALLBACK,
    GROQ_TEMPERATURE,
    GROQ_MAX_TOKENS,
    GROQ_TIMEOUT_SECONDS,
    GROQ_MAX_RETRIES,
)
from config.constants import RETRY_BASE_DELAY_SEC, RETRY_BACKOFF_FACTOR
from utils.logger import get_logger

logger = get_logger(__name__)


class GroqClient:
    """
    Thread-safe Groq API client with retry and fallback model support.

    Wraps the official groq Python SDK to provide:
    - Automatic retry on transient failures
    - Model fallback from Llama 4 Maverick to DeepSeek R1
    - Structured error logging
    - Both streaming and non-streaming completion modes
    """

    def __init__(self) -> None:
        """
        Initialise the Groq client.

        Raises:
            ValueError: If GROQ_API_KEY is not configured.
        """
        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. "
                "Add it to your .env file: GROQ_API_KEY=gsk_..."
            )

        self._client = Groq(
            api_key=GROQ_API_KEY,
            timeout=GROQ_TIMEOUT_SECONDS,
            max_retries=0,  # We handle retries manually for better control
        )
        self._primary_model = GROQ_MODEL_PRIMARY
        self._fallback_model = GROQ_MODEL_FALLBACK
        logger.info(f"GroqClient initialised. Primary model: {self._primary_model}")

    def complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """
        Generate a completion from the Groq API with retry logic.

        Attempts the primary model first. On failure, falls back to the
        secondary model. Uses exponential backoff between retries.

        Args:
            messages: List of ChatML message dicts (role + content).
            temperature: Sampling temperature. Defaults to settings value.
            max_tokens: Max response tokens. Defaults to settings value.
            stream: Whether to use streaming mode (currently returns full text).

        Returns:
            Generated text response as a string.

        Raises:
            RuntimeError: If all retries and model fallback are exhausted.
        """
        temp = temperature if temperature is not None else GROQ_TEMPERATURE
        tokens = max_tokens or GROQ_MAX_TOKENS

        models_to_try = [self._primary_model, self._fallback_model]

        for model in models_to_try:
            result = self._attempt_completion(
                model=model,
                messages=messages,
                temperature=temp,
                max_tokens=tokens,
            )
            if result is not None:
                return result
            logger.warning(f"Model {model} failed. Trying next model...")

        raise RuntimeError(
            "All Groq API attempts failed. "
            "Check your API key, network connection, and model availability."
        )

    def _attempt_completion(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """
        Attempt a single completion with retries against a specific model.

        Args:
            model: Groq model identifier string.
            messages: ChatML message list.
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.

        Returns:
            Response text on success, None if all retries failed.
        """
        delay = RETRY_BASE_DELAY_SEC

        for attempt in range(1, GROQ_MAX_RETRIES + 1):
            try:
                logger.debug(
                    f"Groq request | model={model} | attempt={attempt}/{GROQ_MAX_RETRIES} "
                    f"| messages={len(messages)}"
                )

                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )

                content = response.choices[0].message.content or ""
                usage = response.usage

                logger.info(
                    f"Groq response received | model={model} | "
                    f"prompt_tokens={usage.prompt_tokens if usage else '?'} | "
                    f"completion_tokens={usage.completion_tokens if usage else '?'}"
                )

                return content.strip()

            except RateLimitError as exc:
                # Rate limit — wait longer before retry
                wait = delay * 3
                logger.warning(
                    f"Groq rate limit (attempt {attempt}). "
                    f"Waiting {wait:.1f}s before retry. Error: {exc}"
                )
                time.sleep(wait)

            except APIConnectionError as exc:
                logger.warning(
                    f"Groq connection error (attempt {attempt}/{GROQ_MAX_RETRIES}): {exc}"
                )
                if attempt < GROQ_MAX_RETRIES:
                    time.sleep(delay)
                    delay *= RETRY_BACKOFF_FACTOR

            except APIStatusError as exc:
                # 4xx errors (except 429) are not retryable
                if exc.status_code == 429:
                    logger.warning(f"Groq 429 Too Many Requests. Waiting {delay}s.")
                    time.sleep(delay)
                    delay *= RETRY_BACKOFF_FACTOR
                else:
                    logger.error(
                        f"Groq API error {exc.status_code} (not retryable): {exc.message}"
                    )
                    return None

            except Exception as exc:
                logger.error(
                    f"Unexpected Groq error (attempt {attempt}): {exc}", exc_info=True
                )
                if attempt < GROQ_MAX_RETRIES:
                    time.sleep(delay)
                    delay *= RETRY_BACKOFF_FACTOR

        return None

    def stream_complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """
        Stream completion tokens from Groq for lower perceived latency.

        Yields individual text chunks as they arrive from the API.
        The caller accumulates chunks to build the full response.

        Args:
            messages: ChatML message list.
            temperature: Sampling temperature.
            max_tokens: Max response tokens.

        Yields:
            Individual text delta strings from the streaming response.
        """
        temp = temperature if temperature is not None else GROQ_TEMPERATURE
        tokens = max_tokens or GROQ_MAX_TOKENS

        try:
            stream = self._client.chat.completions.create(
                model=self._primary_model,
                messages=messages,
                temperature=temp,
                max_tokens=tokens,
                stream=True,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        except Exception as exc:
            logger.error(f"Groq streaming error: {exc}", exc_info=True)
            # Fall back to non-streaming on error
            try:
                result = self.complete(messages, temperature=temp, max_tokens=tokens)
                yield result
            except RuntimeError:
                yield (
                    "I'm sorry, I'm having trouble connecting to my knowledge systems. "
                    "Please try again in a moment."
                )
