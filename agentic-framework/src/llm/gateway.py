"""Provider-agnostic gateway for generating framework specifications."""

from __future__ import annotations

import os
from typing import Any

from src.exceptions import (
    ConfigurationError,
    LLMError,
    exception_handler,
    handle_llm_call,
)


class LLMGateway:
    """Select and expose the configured LLM provider."""

    def __init__(self) -> None:
        """Initialize the provider selected by ``LLM_PROVIDER``."""

        provider = (
            os.getenv(
                "LLM_PROVIDER",
                "mock",
            )
            .lower()
            .strip()
        )

        if provider == "mock":

            from src.llm.mock import MockLLMProvider

            self.provider = MockLLMProvider()

            return

        if provider == "gemini":

            from src.llm.llm_providers.gemini_provider import (
                GeminiProvider,
            )

            api_key = os.getenv(
                "GEMINI_API_KEY"
            )

            model = os.getenv(
                "GEMINI_MODEL",
                "gemini-2.0-flash",
            )

            if not api_key:
                raise ConfigurationError(
                    "GEMINI_API_KEY is not configured.",
                    user_message=(
                        "Gemini API key is not configured."
                    ),
                )

            self.provider = GeminiProvider(
                api_key=api_key,
                model=model,
            )

            return

        if provider == "ollama":

            from src.llm.llm_providers.ollama_provider import (
                OllamaProvider,
            )

            model = os.getenv(
                "OLLAMA_MODEL",
                "qwen3:8b",
            )

            host = os.getenv(
                "OLLAMA_HOST",
                "http://localhost:11434",
            )

            self.provider = OllamaProvider(
                model=model,
                host=host,
            )

            return

        if provider == "openai":

            from src.llm.llm_providers.openai_provider import (
                OpenAIProvider,
            )

            api_key = os.getenv(
                "OPENAI_API_KEY"
            )

            model = os.getenv(
                "OPENAI_MODEL",
                "gpt-4o",
            )

            if not api_key:
                raise ConfigurationError(
                    "OPENAI_API_KEY is not configured.",
                    user_message=(
                        "OpenAI API key is not configured."
                    ),
                )

            self.provider = OpenAIProvider(
                api_key=api_key,
                model=model,
            )

            return

        if provider == "anthropic":

            from src.llm.llm_providers.anthropic_provider import (
                AnthropicProvider,
            )

            api_key = os.getenv(
                "ANTHROPIC_API_KEY"
            )

            model = os.getenv(
                "ANTHROPIC_MODEL",
                "claude-sonnet-4-5-20250929",
            )

            if not api_key:
                raise ConfigurationError(
                    "ANTHROPIC_API_KEY is not configured.",
                    user_message=(
                        "Anthropic API key is not configured."
                    ),
                )

            self.provider = AnthropicProvider(
                api_key=api_key,
                model=model,
            )

            return

        raise ConfigurationError(
            f"Unsupported LLM provider: {provider}",
            user_message=(
                f"Unsupported LLM provider: {provider}."
            ),
        )

    # ---------------------------------------------------------
    # GENERATE JSON
    # ---------------------------------------------------------

    @exception_handler("llm.gateway.generate_json")
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Generate and return a structured JSON response."""

        if not system_prompt.strip():
            raise LLMError(
                "System prompt cannot be empty.",
                user_message=(
                    "LLM system prompt cannot be empty."
                ),
            )

        if not user_prompt.strip():
            raise LLMError(
                "User prompt cannot be empty.",
                user_message=(
                    "LLM user prompt cannot be empty."
                ),
            )

        return handle_llm_call(
            "LLM provider JSON generation",
            self.provider.generate_json,
            system_prompt,
            user_prompt,
        )

    # ---------------------------------------------------------
    # GENERATE TEXT
    # ---------------------------------------------------------

    @exception_handler("llm.gateway.generate")
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate and return a text response."""

        if not system_prompt.strip():
            raise LLMError(
                "System prompt cannot be empty.",
                user_message=(
                    "LLM system prompt cannot be empty."
                ),
            )

        if not user_prompt.strip():
            raise LLMError(
                "User prompt cannot be empty.",
                user_message=(
                    "LLM user prompt cannot be empty."
                ),
            )

        return handle_llm_call(
            "LLM provider text generation",
            self.provider.generate,
            system_prompt,
            user_prompt,
        )