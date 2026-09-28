"""Module containing workflow conditions functionality for the Enterprise Agent Framework."""

from typing import Any

from src.exceptions import ValidationError, exception_handler


@exception_handler("workflow.condition.evaluate")
def evaluate_condition(
    condition: str,
    context: dict[str, Any],
) -> bool:
    """Evaluate a workflow condition."""

    condition = condition.strip()

    if not condition:
        raise ValidationError(
            "Condition cannot be empty.",
            user_message="Condition cannot be empty.",
        )

    # -----------------------------------------
    # Contains
    # -----------------------------------------

    if " contains " in condition:

        left, right = condition.split(
            " contains ",
            1,
        )

        value = context.get(left.strip())

        expected = right.strip().strip(
            "\"'"
        )

        if value is None:
            return False

        return expected.lower() in str(
            value
        ).lower()

    # -----------------------------------------
    # Not equals
    # -----------------------------------------

    if "!=" in condition:

        left, right = condition.split(
            "!=",
            1,
        )

        value = context.get(left.strip())

        expected = right.strip().strip(
            "\"'"
        )

        return str(value) != expected

    # -----------------------------------------
    # Greater than or equal
    # -----------------------------------------

    if ">=" in condition:

        left, right = condition.split(
            ">=",
            1,
        )

        value = context.get(left.strip())

        if value is None:
            return False

        try:
            return float(value) >= float(
                right.strip()
            )

        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"Condition values must be numeric: "
                f"{condition}",
                user_message=(
                    "Condition values must be numeric."
                ),
            ) from exc

    # -----------------------------------------
    # Less than or equal
    # -----------------------------------------

    if "<=" in condition:

        left, right = condition.split(
            "<=",
            1,
        )

        value = context.get(left.strip())

        if value is None:
            return False

        try:
            return float(value) <= float(
                right.strip()
            )

        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"Condition values must be numeric: "
                f"{condition}",
                user_message=(
                    "Condition values must be numeric."
                ),
            ) from exc

    # -----------------------------------------
    # Greater than
    # -----------------------------------------

    if ">" in condition:

        left, right = condition.split(
            ">",
            1,
        )

        value = context.get(left.strip())

        if value is None:
            return False

        try:
            return float(value) > float(
                right.strip()
            )

        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"Condition values must be numeric: "
                f"{condition}",
                user_message=(
                    "Condition values must be numeric."
                ),
            ) from exc

    # -----------------------------------------
    # Less than
    # -----------------------------------------

    if "<" in condition:

        left, right = condition.split(
            "<",
            1,
        )

        value = context.get(left.strip())

        if value is None:
            return False

        try:
            return float(value) < float(
                right.strip()
            )

        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"Condition values must be numeric: "
                f"{condition}",
                user_message=(
                    "Condition values must be numeric."
                ),
            ) from exc

    # -----------------------------------------
    # Equals
    # -----------------------------------------

    if "==" in condition:

        left, right = condition.split(
            "==",
            1,
        )

        value = context.get(left.strip())

        expected = right.strip().strip(
            "\"'"
        )

        return str(value) == expected

    raise ValidationError(
        f"Unsupported condition: {condition}",
        user_message="Unsupported workflow condition.",
    )