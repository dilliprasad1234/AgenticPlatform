from typing import Any

from guardrails.base import BaseGuardrail


class FleetDataGroundingGuardrail(BaseGuardrail):
    """Validate basic grounding and completeness of Fleet collector/analyzer output."""

    def __init__(
        self,
        required_collection_fields: list[str] | None = None,
        required_analysis_fields: list[str] | None = None,
    ) -> None:
        self.required_collection_fields = required_collection_fields or []
        self.required_analysis_fields = required_analysis_fields or []

    def validate(self, value: Any, context: dict[str, Any] | None = None) -> tuple[bool, Any]:
        """Reject malformed outputs and unsupported claims of successful collection/analysis."""
        if not isinstance(value, dict):
            return False, "Fleet output must be a structured JSON object."

        if "records" in value:
            missing = [k for k in self.required_collection_fields if k not in value]
            if missing:
                return False, f"Fleet collection output is missing required fields: {missing}."
            if value.get("collection_status") == "success" and not isinstance(value.get("records"), list):
                return False, "Successful fleet collection must contain a records array."

        if "fleet_metrics" in value or "device_analysis" in value:
            missing = [k for k in self.required_analysis_fields if k not in value]
            if missing:
                return False, f"Fleet analysis output is missing required fields: {missing}."

        return True, value
