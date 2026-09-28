"""Module containing base functionality for the Enterprise Agent Framework."""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """
    Base interface for all LLM providers.

    Every LLM provider used by the framework must implement
    generate_json() and generate().
    """

    @abstractmethod
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """
        Generate a structured JSON response from the LLM.

        Args:
            system_prompt: Instructions that define the LLM's behavior.
            user_prompt: The actual request from the application/user.

        Returns:
            A Python dictionary containing the structured response.
        """
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Generate a normal text response from the LLM.

        Args:
            system_prompt: Instructions that define the LLM's behavior.
            user_prompt: The actual request from the application/user.

        Returns:
            A string containing the generated response.
        """
        raise NotImplementedError