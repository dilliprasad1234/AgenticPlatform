"""Module containing agent runtime functionality for the Enterprise Agent Framework."""

from typing import Any

from agents.agent import AgentSpec
from agents.agent_registry import AgentRegistry
from src.exceptions import (
    AgentError,
    ToolError,
    exception_handler,
)
from tools.tool_registry import ToolRegistry


class AgentRuntime:
    """
    Runtime responsible for loading an agent,
    resolving its configured tools and knowledge bases,
    and executing tools.
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        tool_registry: ToolRegistry,
    ):
        """Initialize the object with the supplied configuration."""
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry

    # -----------------------------------------
    # Load Agent
    # -----------------------------------------

    @exception_handler("agent.runtime.load_agent")
    def load_agent(
        self,
        identifier: str,
    ) -> AgentSpec:
        """
        Load an agent specification by ID or name.
        """

        return self.agent_registry.get(
            identifier
        )

    # -----------------------------------------
    # Resolve Tools
    # -----------------------------------------

    @exception_handler("agent.runtime.resolve_tools")
    def resolve_tools(
        self,
        agent: AgentSpec,
    ) -> dict:
        """
        Resolve all tools configured for the agent.
        """

        resolved_tools = {}

        for tool_id in agent.tools:

            try:
                tool = self.tool_registry.get(
                    tool_id
                )

            except Exception as exc:
                raise ToolError(
                    f"Failed to resolve tool '{tool_id}': {exc}",
                    tool_name=tool_id,
                ) from exc

            resolved_tools[tool_id] = tool

        return resolved_tools

    # -----------------------------------------
    # Resolve Knowledge
    # -----------------------------------------

    @exception_handler("agent.runtime.resolve_knowledge")
    def resolve_knowledge(
        self,
        agent: AgentSpec,
    ) -> list[str]:
        """
        Resolve the knowledge bases configured for the agent.
        """

        return list(agent.kb)

    # -----------------------------------------
    # Execute Tool
    # -----------------------------------------

    @exception_handler("agent.runtime.execute_tool")
    def execute_tool(
        self,
        agent: AgentSpec,
        tool_id: str,
        arguments: dict[str, Any],
    ) -> Any:
        """
        Execute a tool configured for the agent.
        """

        # Validate tool is configured
        if tool_id not in agent.tools:
            raise AgentError(
                f"Tool '{tool_id}' is not configured for agent '{agent.id}'.",
                agent_name=agent.id,
                details={"missing_tool_id": tool_id},
            )

        # Resolve tool
        try:
            tool = self.tool_registry.get(
                tool_id
            )

        except Exception as exc:
            raise ToolError(
                f"Failed to resolve tool '{tool_id}': {exc}",
                tool_name=tool_id,
            ) from exc

        # Validate execute method
        if not hasattr(tool, "execute"):
            raise ToolError(
                f"Tool '{tool_id}' does not provide an execute() method.",
                tool_name=tool_id,
            )

        # Execute tool
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