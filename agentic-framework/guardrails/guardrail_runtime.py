"""Module containing guardrail runtime functionality for the Enterprise Agent Framework."""

from __future__ import annotations

from typing import Any

from guardrails.guardrail_registry import GuardrailRegistry
from src.exceptions import exception_handler


class GuardrailRuntime:
    """
    Executes registered guardrails through a consistent framework interface.
    """

    def __init__(self, registry: GuardrailRegistry | None = None):
        """Initialize the object with the supplied configuration."""
        self.registry = registry or GuardrailRegistry()

    @exception_handler("guardrail.runtime.validate")
    def validate(
        self,
        guardrail_id: str,
        value: Any,
        configuration: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, Any]:
        """
        Execute a guardrail using its YAML definition ID.
        """

        spec = self.registry.get_spec(guardrail_id)

        if not spec.enabled:
            return (True, value)

        guardrail_class = self.registry.get_by_id(guardrail_id)

        final_configuration = dict(spec.configuration)

        if configuration:
            final_configuration.update(configuration)

        guardrail = guardrail_class(**final_configuration)

        return guardrail.validate(
            value,
            context=context,
        )