"""Module containing guardrail execution functionality for the Enterprise Agent Framework."""

from __future__ import annotations

from typing import Any

from guardrails.guardrail_runtime import GuardrailRuntime
from src.exceptions import exception_handler


class GuardrailExecution:
    """
    Framework execution layer for guardrails.
    """

    def __init__(self, runtime: GuardrailRuntime | None = None):
        """Initialize the object with the supplied configuration."""
        self.runtime = runtime or GuardrailRuntime()

    @exception_handler("guardrail.execute")
    def execute(
        self,
        guardrail_id: str,
        value: Any,
        configuration: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, Any]:
        """
        Execute a guardrail through the GuardrailRuntime.
        """

        return self.runtime.validate(
            guardrail_id=guardrail_id,
            value=value,
            configuration=configuration,
            context=context,
        )