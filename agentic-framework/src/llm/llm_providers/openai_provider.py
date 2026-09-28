"""OpenAI provider functionality for the Enterprise Agent Framework."""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from src.exceptions import (
    handle_llm_call,
    parse_llm_json,
    validate_llm_content,
)
from src.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(
        self,
        api_key: str,
        model: str,
    ) -> None:
        """Initialize the OpenAI provider."""

        self.client = OpenAI(
            api_key=api_key
        )
        self.model = model

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Generate a JSON response using OpenAI."""

        response = handle_llm_call(
            "OpenAI request",
            self.client.chat.completions.create,
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
            temperature=0,
            response_format={
                "type": "json_object"
            },
        )

        return parse_llm_json(
            response.choices[0].message.content,
            "OpenAI",
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a text response using OpenAI."""

        response = handle_llm_call(
            "OpenAI request",
            self.client.chat.completions.create,
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
            temperature=0,
        )

        return validate_llm_content(
            response.choices[0].message.content,
            "OpenAI",
        )