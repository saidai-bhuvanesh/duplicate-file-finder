"""
LLM client with provider abstraction and fallback.

Supports Groq (primary) and OpenAI (fallback) with:
- Async streaming
- Token counting
- Cost estimation
- Retry logic with exponential backoff
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncGenerator

from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger

logger = get_logger(__name__, component="llm_client")

# Pricing per 1M tokens (input / output) as of 2025
_PRICING: dict[str, dict[str, float]] = {
    # Groq models
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "mixtral-8x7b-32768": {"input": 0.27, "output": 0.27},
    # OpenAI models
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a model call."""
    pricing = _PRICING.get(model, {"input": 1.0, "output": 2.0})
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000


class LLMClient:
    """
    Unified LLM client supporting Groq and OpenAI with automatic fallback.

    Usage:
        client = LLMClient()
        response = await client.complete(messages=[...])
    """

    def __init__(self) -> None:
        self._settings = get_settings().llm
        self._groq_client = None
        self._openai_client = None

    def _get_groq_client(self) -> Any:
        if self._groq_client is None:
            try:
                from groq import AsyncGroq
                if not self._settings.groq_api_key:
                    raise LLMError("Groq API key not configured", provider="groq")
                self._groq_client = AsyncGroq(
                    api_key=self._settings.groq_api_key.get_secret_value()
                )
            except ImportError as exc:
                raise LLMError("groq package not installed", provider="groq") from exc
        return self._groq_client

    def _get_openai_client(self) -> Any:
        if self._openai_client is None:
            try:
                from openai import AsyncOpenAI
                if not self._settings.openai_api_key:
                    raise LLMError("OpenAI API key not configured", provider="openai")
                self._openai_client = AsyncOpenAI(
                    api_key=self._settings.openai_api_key.get_secret_value()
                )
            except ImportError as exc:
                raise LLMError("openai package not installed", provider="openai") from exc
        return self._openai_client

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        """
        Generate a chat completion.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            temperature: Sampling temperature (overrides default).
            max_tokens: Max output tokens (overrides default).
            provider: Force a specific provider ("groq" or "openai").
            retries: Number of retry attempts on failure.

        Returns:
            Dict with keys: content, input_tokens, output_tokens, cost_usd,
                           model, provider, latency_ms
        """
        primary = provider or self._settings.primary_llm_provider
        providers_to_try = [primary]
        if primary == "groq" and self._settings.openai_api_key:
            providers_to_try.append("openai")
        elif primary == "openai" and self._settings.groq_api_key:
            providers_to_try.append("groq")

        last_exc: Exception | None = None
        for attempt in range(retries):
            for prov in providers_to_try:
                try:
                    result = await self._call_provider(
                        provider=prov,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    return result
                except LLMError as exc:
                    last_exc = exc
                    logger.warning(
                        "llm_call_failed",
                        provider=prov,
                        attempt=attempt + 1,
                        error=str(exc),
                    )
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff

        raise LLMError(
            f"All LLM providers failed after {retries} retries: {last_exc}",
        )

    async def _call_provider(
        self,
        provider: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Call a specific provider and return normalized response."""
        start = time.perf_counter()

        if provider == "groq":
            return await self._call_groq(messages, temperature, max_tokens, start)
        elif provider == "openai":
            return await self._call_openai(messages, temperature, max_tokens, start)
        else:
            raise LLMError(f"Unknown provider: {provider}")

    async def _call_groq(
        self,
        messages: list[dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
        start: float,
    ) -> dict[str, Any]:
        try:
            client = self._get_groq_client()
            model = self._settings.groq_model_name
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature or self._settings.groq_temperature,
                max_tokens=max_tokens or self._settings.groq_max_tokens,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            cost = _estimate_cost(model, input_tokens, output_tokens)

            logger.info(
                "llm_call_completed",
                provider="groq",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=round(cost, 6),
                latency_ms=round(latency_ms, 2),
            )
            return {
                "content": response.choices[0].message.content,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "model": model,
                "provider": "groq",
                "latency_ms": latency_ms,
            }
        except Exception as exc:
            raise LLMError(str(exc), provider="groq", model=self._settings.groq_model_name) from exc

    async def _call_openai(
        self,
        messages: list[dict[str, str]],
        temperature: float | None,
        max_tokens: int | None,
        start: float,
    ) -> dict[str, Any]:
        try:
            client = self._get_openai_client()
            model = self._settings.openai_model_name
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature or self._settings.openai_temperature,
                max_tokens=max_tokens or self._settings.openai_max_tokens,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            cost = _estimate_cost(model, input_tokens, output_tokens)

            logger.info(
                "llm_call_completed",
                provider="openai",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=round(cost, 6),
                latency_ms=round(latency_ms, 2),
            )
            return {
                "content": response.choices[0].message.content,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "model": model,
                "provider": "openai",
                "latency_ms": latency_ms,
            }
        except Exception as exc:
            raise LLMError(str(exc), provider="openai", model=self._settings.openai_model_name) from exc
