"""Ollama provider functionality for the Enterprise Agent Framework."""

from __future__ import annotations

from typing import Any

from ollama import Client

from src.exceptions import (
    handle_llm_call,
    parse_llm_json,
    validate_llm_content,
)
from src.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama LLM provider."""

    def __init__(
        self,
        model: str = "qwen3:8b",
        host: str = "http://localhost:11434",
    ) -> None:
        """Initialize the Ollama provider."""

        self.model = model
        self.client = Client(
            host=host
        )

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Generate a JSON response using Ollama."""

        response = handle_llm_call(
            "Ollama request",
            self.client.chat,
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            format="json",
        )

        return parse_llm_json(
            response["message"]["content"],
            "Ollama",
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a text response using Ollama."""

        response = handle_llm_call(
            "Ollama request",
            self.client.chat,
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        return validate_llm_content(
            response["message"]["content"],
            "Ollama",
        )