"""AAVA-style execution trace helpers.

This module records observable execution events for agents, workflows, tools,
RAG/knowledge bases, and guardrails. It deliberately records high-level
operational decisions rather than private model chain-of-thought.
"""
from __future__ import annotations

from typing import Any

from .logging import log_event


def trace_event(
    level: str,
    event: str,
    *,
    component: str,
    trace_view: str,
    message: str = "",
    **fields: Any,
) -> None:
    """Record one AAVA-style observable execution event."""
    log_event(
        level,
        event,
        component=component,
        message=message or event,
        trace_view=trace_view,
        **fields,
    )


def execution_started(agent_name: str, *, agent_id: str, description: str = "", expected_output: str = "", **fields: Any) -> None:
    trace_event("INFO", "trace.execution_started", component="agent", trace_view="execution_started", message="Agent execution started", agent_id=agent_id, agent_name=agent_name, description=description, expected_output=expected_output, **fields)


def task_started(agent_id: str, *, agent_name: str, task_description: str, expected_output: str, **fields: Any) -> None:
    trace_event("INFO", "trace.task_started", component="agent", trace_view="task_started", message="Task started", agent_id=agent_id, agent_name=agent_name, task_description=task_description, expected_output=expected_output, **fields)


def decision(agent_id: str, *, agent_name: str, decision_text: str, reason: str = "", **fields: Any) -> None:
    trace_event("DEBUG", "trace.decision", component="agent", trace_view="decision", message="Agent decision", agent_id=agent_id, agent_name=agent_name, decision=decision_text, reason=reason, **fields)


def tool_initialized(agent_id: str, *, agent_name: str, tool_name: str, tool_class: str = "", arguments: Any = None, **fields: Any) -> None:
    trace_event("INFO", "trace.tool_initialized", component="tool", trace_view="tool_initialized", message="Tool initialized", agent_id=agent_id, agent_name=agent_name, tool_id=fields.pop("tool_id", tool_name), tool_name=tool_name, tool_class=tool_class, arguments=arguments if arguments is not None else {}, **fields)


def tool_action(agent_id: str, *, agent_name: str, tool_name: str, action: str, action_input: Any = None, **fields: Any) -> None:
    trace_event("DEBUG", "trace.tool_action", component="tool", trace_view="tool_action", message="Tool action", agent_id=agent_id, agent_name=agent_name, tool_id=fields.pop("tool_id", tool_name), tool_name=tool_name, action=action, action_input=action_input if action_input is not None else {}, **fields)


def tool_observation(agent_id: str, *, agent_name: str, tool_name: str, observation: Any, status: str = "success", **fields: Any) -> None:
    level = "INFO" if status.lower() == "success" else "ERROR"
    trace_event(level, "trace.tool_observation", component="tool", trace_view="tool_observation", message="Tool observation", agent_id=agent_id, agent_name=agent_name, tool_id=fields.pop("tool_id", tool_name), tool_name=tool_name, status=status, observation=observation, **fields)


def llm_started(agent_id: str, *, agent_name: str, provider: str = "", model: str = "", **fields: Any) -> None:
    trace_event("DEBUG", "trace.llm_started", component="agent", trace_view="llm_started", message="LLM call started", agent_id=agent_id, agent_name=agent_name, provider=provider, model=model, **fields)


def llm_completed(agent_id: str, *, agent_name: str, **fields: Any) -> None:
    trace_event("DEBUG", "trace.llm_completed", component="agent", trace_view="llm_completed", message="LLM call completed", agent_id=agent_id, agent_name=agent_name, **fields)


def agent_finished(agent_id: str, *, agent_name: str, final_answer: Any, **fields: Any) -> None:
    trace_event("INFO", "trace.agent_finished", component="agent", trace_view="agent_finished", message="Agent finished", agent_id=agent_id, agent_name=agent_name, final_answer=final_answer, **fields)


def task_finished(agent_id: str, *, agent_name: str, final_answer: Any, status: str = "success", **fields: Any) -> None:
    level = "INFO" if status.lower() == "success" else "ERROR"
    trace_event(level, "trace.task_finished", component="agent", trace_view="task_finished", message="Task finished", agent_id=agent_id, agent_name=agent_name, status=status, final_answer=final_answer, **fields)


def execution_completed(agent_id: str, *, agent_name: str, final_answer: Any, status: str = "success", **fields: Any) -> None:
    level = "INFO" if status.lower() == "success" else "ERROR"
    trace_event(level, "trace.execution_completed", component="agent", trace_view="execution_completed", message="Execution completed", agent_id=agent_id, agent_name=agent_name, status=status, final_answer=final_answer, **fields)


# Generic component lifecycle helpers used by workflow/tool/RAG/guardrail runtimes.
def component_started(component: str, *, name: str, event: str | None = None, **fields: Any) -> None:
    view = event or f"{component}_started"
    trace_event("INFO", f"trace.{view}", component=component, trace_view=view, message=f"{component.title()} execution started", **{f"{component}_name": name, "name": name, **fields})


def component_completed(component: str, *, name: str, status: str = "success", event: str | None = None, result: Any = None, **fields: Any) -> None:
    view = event or f"{component}_completed"
    level = "INFO" if status.lower() == "success" else "ERROR"
    trace_event(level, f"trace.{view}", component=component, trace_view=view, message=f"{component.title()} execution completed", **{f"{component}_name": name, "name": name, "status": status, "result": result, **fields})


def component_failed(component: str, *, name: str, error: Any, event: str | None = None, **fields: Any) -> None:
    view = event or f"{component}_failed"
    trace_event("ERROR", f"trace.{view}", component=component, trace_view=view, message=f"{component.title()} execution failed", **{f"{component}_name": name, "name": name, "status": "failed", "error": str(error), "error_type": type(error).__name__, **fields})
