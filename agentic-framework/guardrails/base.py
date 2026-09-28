"""Module containing base functionality for the Enterprise Agent Framework."""

from abc import ABC, abstractmethod
from typing import Any


class BaseGuardrail(ABC):
    """
    Base contract for every guardrail in the framework.

    A guardrail receives a value, validates it,
    and returns whether the value is acceptable.
    """

    @abstractmethod
    def validate(
        self,
        value: Any,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, Any]:
        """
        Validate the provided value.

        Returns:
            (True, value)  -> validation passed
            (False, reason) -> validation failed
        """
        pass