"""Module containing tool runtime functionality for the Enterprise Agent Framework."""

from typing import Any

from src.exceptions import (
    ToolError,
    exception_handler,
)
from tools.tool_registry import ToolRegistry


class ToolRuntime:
    """
    Runtime responsible for resolving and executing tools.
    """

    def __init__(self, tool_registry: ToolRegistry):
        """Initialize the object with the supplied configuration."""
        self.tool_registry = tool_registry

    @exception_handler("tool.runtime.execute")
    def execute(
        self,
        tool_id: str,
        arguments: dict[str, Any],
    ) -> Any:
        """
        Resolve a tool from the registry and execute it
        with the provided arguments.
        """

        # --------------------------------------------------
        # Resolve tool
        # --------------------------------------------------

        try:
            tool = self.tool_registry.get(
                tool_id
            )

        except Exception as exc:
            raise ToolError(
                f"Failed to resolve tool '{tool_id}': {exc}",
                tool_name=tool_id,
            ) from exc

        # --------------------------------------------------
        # Validate executable tool
        # --------------------------------------------------

        if not hasattr(
            tool,
            "execute",
        ):
            raise ToolError(
                f"Tool '{tool_id}' does not provide an execute() method.",
                tool_name=tool_id,
            )

        # --------------------------------------------------
        # Execute tool
        # --------------------------------------------------

        try:
            return tool.execute(
                **arguments
            )

        except ToolError:
            raise

        except Exception as exc:
            raise ToolError(
                f"Tool '{tool_id}' execution failed: {exc}",
                tool_name=tool_id,
                tool_input=arguments,
            ) from exc