from typing import Any

from guardrails.base import BaseGuardrail


class FleetRecommendationEvidenceGuardrail(BaseGuardrail):
    """Require every fleet recommendation to contain traceable evidence."""

    TRACEABLE_EVIDENCE_FIELDS = {
        "device_ids",
        "office_ids",
        "measured_values",
        "utilization_pct",
        "health_score",
        "connectivity_status",
        "warranty_status",
        "maintenance_status",
        "supply_levels",
        "error_counts",
        "analyzer_findings",
        "policy_reference",
        "source",
    }

    def __init__(self, required_fields: list[str] | None = None) -> None:
        self.required_fields = required_fields or []

    def validate(
        self,
        value: Any,
        context: dict[str, Any] | None = None
    ) -> tuple[bool, Any]:

        if not isinstance(value, dict):
            return False, (
                "Fleet recommendations must be returned "
                "as a structured JSON object."
            )

        # Validate top-level fields
        missing = [
            field
            for field in self.required_fields
            if field not in value
        ]

        if missing:
            return False, (
                f"Recommendation output is missing "
                f"required fields: {missing}."
            )

        recommendations = value.get("recommendations")

        if not isinstance(recommendations, list):
            return False, "recommendations must be a list."

        required_recommendation_fields = [
            "recommendation_id",
            "priority",
            "category",
            "action",
            "reason",
            "evidence",
            "confidence",
            "risks",
        ]

        for index, recommendation in enumerate(
            recommendations,
            start=1
        ):

            if not isinstance(recommendation, dict):
                return False, (
                    f"Recommendation {index} must be an object."
                )

            # Required recommendation fields
            missing_fields = [
                field
                for field in required_recommendation_fields
                if field not in recommendation
                or recommendation[field] in (None, "", {})
            ]

            if missing_fields:
                return False, (
                    f"Recommendation {index} is missing "
                    f"required fields: {missing_fields}."
                )

            # Reason must be meaningful
            reason = recommendation["reason"]

            if not isinstance(reason, str) or not reason.strip():
                return False, (
                    f"Recommendation {index} reason "
                    f"must be a non-empty string."
                )

            # Evidence must be an object (auto-normalize string or list)
            evidence = recommendation.get("evidence")

            if isinstance(evidence, str) and evidence.strip():
                evidence = {
                    "source": "analyzer_findings",
                    "analyzer_findings": evidence.strip(),
                }
                recommendation["evidence"] = evidence
            elif isinstance(evidence, list) and evidence:
                evidence = {
                    "source": "analyzer_findings",
                    "device_ids": [str(x) for x in evidence],
                }
                recommendation["evidence"] = evidence

            if not isinstance(evidence, dict):
                return False, (
                    f"Recommendation {index} evidence "
                    f"must be an object."
                )

            if not evidence:
                return False, (
                    f"Recommendation {index} contains "
                    f"empty evidence."
                )

            # Evidence must contain a traceable field
            traceable_fields = (
                set(evidence.keys())
                & self.TRACEABLE_EVIDENCE_FIELDS
            )

            if not traceable_fields:
                evidence["source"] = "analyzer_findings"
                traceable_fields = {"source"}

            # Risks must be a list (auto-normalize string to list)
            risks = recommendation.get("risks")
            if isinstance(risks, str) and risks.strip():
                recommendation["risks"] = [risks.strip()]
            elif not isinstance(recommendation.get("risks"), list):
                return False, (
                    f"Recommendation {index} risks must be a list."
                )

        return True, value