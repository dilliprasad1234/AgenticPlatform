"""Gemini provider functionality for the Enterprise Agent Framework."""

from __future__ import annotations

from typing import Any

from google import genai

from src.exceptions import (
    handle_llm_call,
    parse_llm_json,
    validate_llm_content,
)
from src.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini LLM provider."""

    def __init__(
        self,
        api_key: str,
        model: str,
    ) -> None:
        """Initialize the Gemini provider."""

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = model

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Generate a JSON response using Gemini."""

        response = handle_llm_call(
            "Gemini request",
            self.client.models.generate_content,
            model=self.model,
            contents=user_prompt,
            config={
                "system_instruction": system_prompt,
                "temperature": 0,
                "response_mime_type": "application/json",
            },
        )

        return parse_llm_json(
            response.text,
            "Gemini",
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a text response using Gemini."""

        response = handle_llm_call(
            "Gemini request",
            self.client.models.generate_content,
            model=self.model,
            contents=user_prompt,
            config={
                "system_instruction": system_prompt,
                "temperature": 0,
            },
        )

        return validate_llm_content(
            response.text,
            "Gemini",
        )