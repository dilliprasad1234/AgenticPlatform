"""
Audit logging for guardrail events.
"""

import logging
from typing import Any
from datetime import datetime, timezone


class GuardrailAuditLogger:
    """
    Logs guardrail execution events for audit and observability.
    """

    def __init__(self, logger_name: str = "guardrails.audit"):
        """Initialize the object with the supplied configuration."""
        self.logger = logging.getLogger(logger_name)

    def log_guardrail_executed(
        self,
        guardrail_id: str,
        guardrail_type: str,
        passed: bool,
        action: str,
        reason: str | None = None,
        enabled: bool = True,
    ):
        """Log a guardrail execution event."""

        event_data = {
            "event": "guardrail_executed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail_id": guardrail_id,
            "guardrail_type": guardrail_type,
            "passed": passed,
            "action": action,
            "enabled": enabled,
        }

        if reason:
            event_data["reason"] = reason

        if passed:
            self.logger.info(
                f"Guardrail '{guardrail_id}' ({guardrail_type}) passed. "
                f"Action: {action}",
                extra=event_data,
            )
        else:
            if action == "block":
                self.logger.warning(
                    f"Guardrail '{guardrail_id}' ({guardrail_type}) failed "
                    f"(BLOCK). Reason: {reason}",
                    extra=event_data,
                )
            elif action == "warn":
                self.logger.warning(
                    f"Guardrail '{guardrail_id}' ({guardrail_type}) failed "
                    f"(WARN). Reason: {reason}",
                    extra=event_data,
                )
            else:
                self.logger.warning(
                    f"Guardrail '{guardrail_id}' ({guardrail_type}) failed. "
                    f"Reason: {reason}",
                    extra=event_data,
                )

    def log_input_guardrail_executed(
        self,
        guardrail_id: str,
        input_key: str,
        passed: bool,
        reason: str | None = None,
    ):
        """Log input guardrail execution."""

        event_data = {
            "event": "input_guardrail_executed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail_id": guardrail_id,
            "input_key": input_key,
            "passed": passed,
        }

        if reason:
            event_data["reason"] = reason

        if passed:
            self.logger.info(
                f"Input guardrail '{guardrail_id}' for '{input_key}' passed.",
                extra=event_data,
            )
        else:
            self.logger.warning(
                f"Input guardrail '{guardrail_id}' for '{input_key}' failed: {reason}",
                extra=event_data,
            )

    def log_output_guardrail_executed(
        self,
        guardrail_id: str,
        passed: bool,
        action: str,
        reason: str | None = None,
    ):
        """Log output guardrail execution."""

        event_data = {
            "event": "output_guardrail_executed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail_id": guardrail_id,
            "passed": passed,
            "action": action,
        }

        if reason:
            event_data["reason"] = reason

        if passed:
            self.logger.info(
                f"Output guardrail '{guardrail_id}' passed.",
                extra=event_data,
            )
        else:
            if action == "block":
                self.logger.warning(
                    f"Output guardrail '{guardrail_id}' failed (BLOCK): {reason}",
                    extra=event_data,
                )
            elif action == "warn":
                self.logger.warning(
                    f"Output guardrail '{guardrail_id}' failed (WARN): {reason}",
                    extra=event_data,
                )

    def log_agent_execution_with_guardrails(
        self,
        agent_id: str,
        input_guardrails: list[str],
        output_guardrails: list[str],
    ):
        """Log that an agent execution will use guardrails."""

        event_data = {
            "event": "agent_execution_with_guardrails",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "input_guardrails": input_guardrails,
            "output_guardrails": output_guardrails,
        }

        self.logger.info(
            f"Agent '{agent_id}' executing with "
            f"{len(input_guardrails)} input guardrails "
            f"and {len(output_guardrails)} output guardrails.",
            extra=event_data,
        )
