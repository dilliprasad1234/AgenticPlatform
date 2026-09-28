from typing import Any

from guardrails.base import BaseGuardrail


class McpReadOnlyGuardrail(BaseGuardrail):
    """Validate that MCP requests stay within the Fleet read-only contract."""

    def __init__(self, allowed_operations: list[str] | None = None) -> None:
        self.allowed_operations = set(allowed_operations or [])

    def validate(self, value: Any, context: dict[str, Any] | None = None) -> tuple[bool, Any]:
        """Reject explicit MCP operation requests that are not read-only."""
        if not isinstance(value, dict):
            return True, value

        operation = value.get("operation")
        if operation is None:
            return True, value

        if operation not in self.allowed_operations:
            return False, f"MCP operation '{operation}' is not permitted for Fleet read-only access."

        if operation == "pg_execute_query":
            query = str((value.get("arguments") or {}).get("query", "")).strip().lower()
            if query and not query.startswith(("select ", "with ", "show ", "explain ")):
                return False, "pg_execute_query is restricted to read-only SQL (SELECT/WITH/SHOW/EXPLAIN)."

        return True, value
