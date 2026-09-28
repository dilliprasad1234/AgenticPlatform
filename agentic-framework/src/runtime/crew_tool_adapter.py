"""Module containing crew tool adapter functionality for the Enterprise Agent Framework."""

from typing import Any

from crewai.tools import BaseTool as CrewAIBaseTool
from pydantic import (
    BaseModel,
    create_model,
    model_validator,
)

from src.exceptions import exception_handler

from src.observability import (
    log_event,
    span,
    tool_initialized as trace_tool_initialized,
    tool_action as trace_tool_action,
    tool_observation as trace_tool_observation,
)


class CrewAIToolAdapter(CrewAIBaseTool):
    """
    Adapter that converts an Enterprise Agent Framework
    tool into a CrewAI-compatible tool and records detailed
    tool execution telemetry.
    """

    framework_tool: Any
    agent_id: str = ""
    agent_name: str = ""

    def __init__(
        self,
        framework_tool: Any,
        name: str,
        description: str,
        args_schema: type,
        agent_id: str = "",
        agent_name: str = "",
    ):
        """Initialize the object with the supplied configuration."""
        super().__init__(
            framework_tool=framework_tool,
            name=name,
            description=description,
            args_schema=args_schema,
        )

        log_event(
            "DEBUG",
            "tool.adapter_created",
            component="tool",
            message=f"CrewAI tool adapter created: {name}",
            tool_name=name,
        )

    @exception_handler("tool.adapter.run")
    def _run(self, **kwargs: Any) -> Any:
        """Internal helper for _run."""
        tool_name = self.name
        if len(kwargs) == 1 and "arguments" in kwargs and isinstance(kwargs["arguments"], dict):
            if "operation" in kwargs["arguments"]:
                kwargs = kwargs["arguments"]

        log_event(
            "INFO",
            "tool.call_started",
            component="tool",
            message=f"Agent invoked tool: {tool_name}",
            tool_name=tool_name,
            arguments=kwargs,
            argument_keys=list(kwargs.keys()),
        )

        # AAVA-style trace: record the observable tool decision/action, not private chain-of-thought.
        if self.agent_id:
            trace_tool_initialized(
                self.agent_id, agent_name=self.agent_name, tool_name=tool_name,
                tool_class=type(self.framework_tool).__name__, arguments=kwargs,
            )
            trace_tool_action(
                self.agent_id, agent_name=self.agent_name, tool_name=tool_name,
                action=f"Execute {tool_name}", action_input=kwargs,
            )

        try:
            with span(
                "tool.call",
                component="tool",
                tool_name=tool_name,
            ):
                result = self.framework_tool.execute(
                    **kwargs
                )

            log_event(
                "INFO",
                "tool.call_completed",
                component="tool",
                message=f"Tool completed: {tool_name}",
                tool_name=tool_name,
                result=result,
            )

            if self.agent_id:
                trace_tool_observation(
                    self.agent_id, agent_name=self.agent_name, tool_name=tool_name,
                    observation=result, status="success",
                )

            return result

        except Exception as exc:
            log_event(
                "ERROR",
                "tool.call_failed",
                component="tool",
                message=f"Tool failed: {tool_name}",
                tool_name=tool_name,
                arguments=kwargs,
            )
            if self.agent_id:
                trace_tool_observation(
                    self.agent_id, agent_name=self.agent_name, tool_name=tool_name,
                    observation="Tool execution failed", status="failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            raise


class DynamicToolInput(BaseModel):
    """Base model for dynamically generated tool schemas with nested argument unwrapping."""

    @model_validator(mode="before")
    @classmethod
    def _unwrap_arguments(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "arguments" in data and isinstance(data["arguments"], dict):
                inner = data["arguments"]
                if "operation" in inner or not any(k in data for k in cls.model_fields if k != "arguments"):
                    unwrapped = dict(inner)
                    for k, v in data.items():
                        if k != "arguments":
                            unwrapped.setdefault(k, v)
                    return unwrapped
        return data


def create_tool_schema(tool_spec):
    """
    Create a Pydantic input schema dynamically from ToolSpec.
    """
    fields = {}

    for input_spec in tool_spec.inputs:
        python_type = {
            "str": str,
            "string": str,
            "int": int,
            "integer": int,
            "float": float,
            "bool": bool,
            "boolean": bool,
            "list": list,
            "dict": dict,
            "object": dict,
        }.get(
            input_spec.type.lower(),
            str,
        )

        default = (
            ...
            if input_spec.required
            else None
        )

        fields[input_spec.name] = (
            python_type,
            default,
        )

    return create_model(
        f"{tool_spec.name.replace(' ', '')}Input",
        __base__=DynamicToolInput,
        **fields,
    )