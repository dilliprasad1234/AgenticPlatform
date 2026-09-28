"""Anthropic provider functionality for the Enterprise Agent Framework."""

from __future__ import annotations

import re
from typing import Any

from anthropic import Anthropic

from src.exceptions import (
    handle_llm_call,
    parse_llm_json,
    validate_llm_content,
)
from src.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic LLM provider."""

    def __init__(
        self,
        api_key: str,
        model: str,
    ) -> None:
        """Initialize the Anthropic provider."""

        self.client = Anthropic(
            api_key=api_key
        )
        self.model = model

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Generate a JSON response using Anthropic."""

        response = handle_llm_call(
            "Anthropic request",
            self.client.messages.create,
            model=self.model,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            temperature=0,
            max_tokens=4096,
        )

        content = validate_llm_content(
            response.content[0].text,
            "Anthropic",
        )

        clean_text = re.sub(
            r"^```(?:json)?\s*",
            "",
            content,
            flags=re.IGNORECASE,
        )

        clean_text = re.sub(
            r"\s*```$",
            "",
            clean_text,
        ).strip()

        return parse_llm_json(
            clean_text,
            "Anthropic",
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a text response using Anthropic."""

        response = handle_llm_call(
            "Anthropic request",
            self.client.messages.create,
            model=self.model,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            temperature=0,
            max_tokens=4096,
        )

        return validate_llm_content(
            response.content[0].text,
            "Anthropic",
        )