"""CrewAI-backed runtime for building and executing framework agents."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from agents.agent_registry import AgentRegistry
from agents.agent_runtime import AgentRuntime
from guardrails import GuardrailExecution, GuardrailRegistry
from guardrails.guardrail_audit import GuardrailAuditLogger
from guardrails.guardrail_runtime import GuardrailRuntime
from src import config
from src.exceptions import (
    AgentError,
    exception_handler,
    translate_runtime_error,
)
from src.observability import (
    TRACE_ID,
    end_run,
    log_event,
    span,
    start_run,
)
from src.rag.retriever import Retriever
from src.rag.vector_store import VectorStore
from src.runtime.crew_tool_adapter import CrewAIToolAdapter, create_tool_schema
from src.runtime.crewai_adapter import CrewAIRuntimeAdapter
from src.runtime.llm_resolver import resolve_crewai_llm
from src.utils.file_manager import extract_file_content
from tools.tool_registry import ToolRegistry


class CrewRuntime:
    """Build and execute agents through CrewAI with logging and guardrails."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        tool_registry: ToolRegistry,
        guardrail_registry: GuardrailRegistry | None = None,
    ) -> None:
        """Initialize the runtime with the framework registries."""
        self.agent_runtime = AgentRuntime(agent_registry, tool_registry)
        self.tool_registry = tool_registry
        self.crewai_adapter = CrewAIRuntimeAdapter()
        self.guardrail_registry = guardrail_registry or GuardrailRegistry()
        self.guardrail_execution = GuardrailExecution(
            runtime=GuardrailRuntime(self.guardrail_registry)
        )
        self.guardrail_audit = GuardrailAuditLogger()

        log_event(
            "DEBUG",
            "crew.runtime_initialized",
            component="framework",
            message="Crew runtime initialized.",
        )

    def build_agent(
        self,
        identifier: str,
        llm: Any | None = None,
    ) -> Any:
        """Load an agent definition, bind its tools, and build a CrewAI agent."""
        with span("agent.build", component="agent", agent_id=identifier):
            log_event(
                "INFO",
                "agent.definition_loading",
                component="agent",
                message="Loading agent definition.",
                agent_id=identifier,
            )

            agent_spec = self.agent_runtime.load_agent(identifier)
            framework_tools = self.agent_runtime.resolve_tools(agent_spec)
            crew_tools = []

            for tool_id, framework_tool in framework_tools.items():
                with span(
                    "agent.tool_binding",
                    component="agent",
                    agent_id=identifier,
                    tool_id=tool_id,
                ):
                    tool_spec = self.tool_registry.get_spec(tool_id)
                    args_schema = create_tool_schema(tool_spec)
                    tool_desc = (
                        framework_tool.get_description()
                        if hasattr(framework_tool, "get_description")
                        else tool_spec.description
                    ) or tool_spec.description
                    crew_tools.append(
                        CrewAIToolAdapter(
                            framework_tool=framework_tool,
                            name=tool_spec.name,
                            description=tool_desc,
                            args_schema=args_schema,
                        )
                    )
                    log_event(
                        "DEBUG",
                        "agent.tool_bound",
                        component="agent",
                        message="Framework tool bound to CrewAI agent.",
                        agent_id=identifier,
                        tool_id=tool_id,
                        tool_name=tool_spec.name,
                    )

            if llm is None:
                llm = self._create_llm()

            result = self.crewai_adapter.build_agent(
                agent_spec,
                tools=crew_tools,
                llm=llm,
            )
            log_event(
                "INFO",
                "agent.built",
                component="agent",
                message=f"Agent built successfully: {agent_spec.agent.name}",
                agent_id=identifier,
                agent_name=agent_spec.agent.name,
                tool_count=len(framework_tools),
            )
            return result

    def _create_llm(self) -> Any:
        """Resolve the execution LLM from the configured provider."""
        provider = os.getenv("EXECUTION_LLM_PROVIDER") or os.getenv(
            "LLM_PROVIDER", "mock"
        )
        log_event(
            "INFO",
            "llm.initializing",
            component="framework",
            message="Resolving execution LLM.",
            provider=provider,
        )
        
        return resolve_crewai_llm()

    def _retrieve_knowledge(
        self,
        agent_spec: Any,
        query: str,
    ) -> str:
        """
        Retrieve relevant knowledge-base content configured
        for the agent.
        """
        knowledge_bases = self.agent_runtime.resolve_knowledge(
            agent_spec
        )
        if not knowledge_bases:
            return ""

        retrieved_context: list[str] = []

        for collection_name in knowledge_bases:
            store = VectorStore(
                persist_path=config.CHROMADB_PATH,
                collection_name=collection_name,
            )

            retriever = Retriever(
                store=store,
                top_k=5,
            )

            results = retriever.retrieve_with_sources(
                query
            )

            for item in results:

                text = item.get("text", "").strip()
                source = item.get("source", "unknown")

                if not text:
                    continue

                retrieved_context.append(
                    f"[Source: {source}]\n{text}"
                )

        if not retrieved_context:
            return ""

        return "\n\n".join(retrieved_context)


    @staticmethod
    def _guardrail_ids(agent_spec: Any) -> list[str]:
        """Return configured guardrail IDs while accepting legacy formats."""
        configured = getattr(agent_spec, "guardrails", []) or []
        if isinstance(configured, dict):
            values: list[str] = []
            for item in configured.values():
                if isinstance(item, list):
                    values.extend(str(v) for v in item)
                elif item:
                    values.append(str(item))
            return list(dict.fromkeys(values))
        if isinstance(configured, list):
            return [str(v) for v in configured]
        return [str(configured)]

    def _applies_to_input(self, guardrail_id: str) -> bool:
        """Return whether a guardrail definition applies to input content."""
        spec = self.guardrail_registry.get_spec(guardrail_id)
        guardrail_type = spec.type.lower()
        return guardrail_type in {"input", "content", "both"}

    def _applies_to_output(self, guardrail_id: str) -> bool:
        """Return whether a guardrail definition applies to output content."""
        spec = self.guardrail_registry.get_spec(guardrail_id)
        guardrail_type = spec.type.lower()
        return guardrail_type in {"output", "content", "both"}

    def _handle_failure(
        self,
        guardrail_id: str,
        result: Any,
        *,
        phase: str,
    ) -> None:
        """Apply the configured guardrail action to a failed validation."""
        spec = self.guardrail_registry.get_spec(guardrail_id)
        action = (spec.action or "block").lower()
        self.guardrail_audit.log_guardrail_executed(
            guardrail_id=guardrail_id,
            guardrail_type=spec.type,
            passed=False,
            action=action,
            reason=str(result),
            enabled=spec.enabled,
        )
        if action != "warn":
            raise ValueError(
                f"{phase.capitalize()} guardrail '{guardrail_id}' failed: {result}"
            )
        log_event(
            "WARNING",
            "guardrail.warning",
            component="guardrail",
            message=f"{phase.capitalize()} guardrail warning: {guardrail_id}",
            guardrail_id=guardrail_id,
            reason=str(result),
        )

    def _validate_inputs(
        self,
        agent_spec: Any,
        inputs: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Validate configured input guardrails before starting CrewAI."""
        if inputs is None:
            return None

        validated = dict(inputs)
        for guardrail_id in self._guardrail_ids(agent_spec):
            if not self._applies_to_input(guardrail_id):
                continue
            for key, value in list(validated.items()):
                passed, result = self.guardrail_execution.execute(
                    guardrail_id=guardrail_id,
                    value=value,
                    context={"agent_id": agent_spec.id, "input_key": key},
                )
                spec = self.guardrail_registry.get_spec(guardrail_id)
                self.guardrail_audit.log_input_guardrail_executed(
                    guardrail_id=guardrail_id,
                    input_key=key,
                    passed=passed,
                    reason=None if passed else str(result),
                )
                if not passed:
                    self._handle_failure(
                        guardrail_id, result, phase="input"
                    )
                else:
                    validated[key] = result
                    self.guardrail_audit.log_guardrail_executed(
                        guardrail_id=guardrail_id,
                        guardrail_type=spec.type,
                        passed=True,
                        action=spec.action,
                        enabled=spec.enabled,
                    )
        return validated

    def _validate_output(
        self,
        agent_spec: Any,
        output: Any,
    ) -> Any:
        """Validate configured output guardrails after CrewAI execution."""
        validated = output
        for guardrail_id in self._guardrail_ids(agent_spec):
            if not self._applies_to_output(guardrail_id):
                continue

            value_for_validation = validated
            if not isinstance(value_for_validation, (str, dict, list, int, float, bool, type(None))):
                value_for_validation = str(value_for_validation)

            passed, result = self.guardrail_execution.execute(
                guardrail_id=guardrail_id,
                value=value_for_validation,
                context={"agent_id": agent_spec.id, "phase": "output"},
            )
            spec = self.guardrail_registry.get_spec(guardrail_id)

            if not passed:
                self._handle_failure(
                    guardrail_id, result, phase="output"
                )
                continue

            self.guardrail_audit.log_guardrail_executed(
                guardrail_id=guardrail_id,
                guardrail_type=spec.type,
                passed=True,
                action=spec.action,
                enabled=spec.enabled,
            )
            validated = result

        return validated

    @staticmethod
    def _normalize_output(result: Any) -> Any:
        """Convert CrewAI output to a useful JSON object when possible."""
        if hasattr(result, "json_dict") and result.json_dict:
            return result.json_dict

        raw_text = result.raw if hasattr(result, "raw") else str(result)
        clean_text = re.sub(
            r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE
        )
        clean_text = re.sub(r"\s*```$", "", clean_text).strip()

        try:
            return json.loads(clean_text)
        except (json.JSONDecodeError, TypeError):
            return raw_text
        
    @exception_handler("agent.runtime.execute")
    def execute(
        self,
        identifier: str,
        task_description: str | None = None,
        expected_output: str | None = None,
        inputs: dict | None = None,
        llm: Any | None = None,
    ) -> Any:
        """Execute one configured agent and return its validated result."""

        agent_id = identifier

        # Preserve an existing workflow trace so agent/tool events remain
        # correlated to the same execution.
        owns_run = TRACE_ID.get() == "-"

        if owns_run:
            start_run(
                run_type="agent_runtime",
                name=identifier,
                agent_id=agent_id,
            )
        else:
            log_event(
                "INFO",
                "agent.execution_started",
                component="agent",
                message=f"Agent execution started: {identifier}",
                agent_id=agent_id,
            )

        try:
            agent_spec = self.agent_runtime.load_agent(identifier)

            inputs = self._validate_inputs(
                agent_spec,
                inputs,
            )

            agent = self.build_agent(
                identifier,
                llm=llm,
            )

            if task_description is None:
                task_description = (
                    getattr(
                        agent_spec.behaviour,
                        "description",
                        None,
                    )
                    or "Execute the configured agent task using the provided input."
                )

            prompt_rules: list[str] = []
            if getattr(agent_spec, "prompt", None):
                for group in agent_spec.prompt:
                    if isinstance(group, list):
                        for item in group:
                            if isinstance(item, str) and item.strip():
                                prompt_rules.append(f"- {item.strip()}")
                    elif isinstance(group, str) and group.strip():
                        prompt_rules.append(f"- {group.strip()}")

            if prompt_rules:
                task_description = (
                    f"{task_description}\n\n"
                    "Agent Guidelines and Instructions:\n"
                    + "\n".join(prompt_rules)
                )

            if inputs:
                runtime_input = dict(inputs)

                file_path = runtime_input.get("file_path")

                if file_path:
                    file_content = extract_file_content(
                        Path(file_path)
                    )

                    runtime_input["file_content"] = file_content

                if list(runtime_input.keys()) == ["user_input"]:
                    task_description = (
                        f"{task_description}\n\n"
                        f"Runtime Input:\n{runtime_input['user_input']}"
                    )
                else:
                    task_description = (
                        f"{task_description}\n\n"
                        f"Runtime Input:\n{runtime_input}"
                    )

            knowledge_context = self._retrieve_knowledge(
                agent_spec,
                task_description,
            )

            if knowledge_context:
                task_description = (
                    f"{task_description}\n\n"
                    "Relevant Knowledge Base Context:\n"
                    f"{knowledge_context}"
                )

            if expected_output is None:
                expected_output = (
                    getattr(
                        agent_spec.behaviour,
                        "expected_output",
                        None,
                    )
                    or "Return the result as valid JSON."
                )

            try:
                from crewai import Crew, Process, Task

            except ImportError as exc:
                raise RuntimeError(
                    "CrewAI is required for agent execution. "
                    "Install the runtime dependencies with "
                    "`pip install -e .`."
                ) from exc

            log_event(
                "DEBUG",
                "agent.task_created",
                component="agent",
                message="Standalone agent task created.",
                agent_id=agent_id,
                expected_output=expected_output,
            )

            task = Task(
                description=task_description,
                expected_output=expected_output,
                agent=agent,
            )

            with span(
                "crewai.agent.kickoff",
                component="agent",
                agent_id=agent_id,
            ):
                try:
                    crew = Crew(
                        agents=[agent],
                        tasks=[task],
                        process=Process.sequential,
                        verbose=True,
                    )
                    result = crew.kickoff()

                except AgentError:
                    raise

                except Exception as exc:
                    user_msg = translate_runtime_error(
                        exc,
                        default_message=(
                            "Agent execution failed during CrewAI execution. "
                            f"Reason: {exc}"
                        ),
                    )

                    raise AgentError(
                        f"CrewAI agent execution failed: {exc}",
                        user_message=user_msg,
                    ) from exc

            normalized = self._normalize_output(result)

            validated = self._validate_output(
                agent_spec,
                normalized,
            )

            log_event(
                "INFO",
                "agent.crew_completed",
                component="agent",
                message="CrewAI agent execution completed.",
                agent_id=agent_id,
                result=validated,
            )

            if owns_run:
                end_run(
                    status="success",
                    run_type="agent_runtime",
                    agent_id=agent_id,
                )
            else:
                log_event(
                    "INFO",
                    "agent.execution_completed",
                    component="agent",
                    message=f"Agent execution completed: {identifier}",
                    agent_id=agent_id,
                )

            return validated

        except Exception:
            # Do NOT call log_exception() here.
            # @exception_handler already handles exception logging.

            if owns_run:
                end_run(
                    status="failed",
                    run_type="agent_runtime",
                    agent_id=agent_id,
                )
            else:
                log_event(
                    "ERROR",
                    "agent.execution_failed",
                    component="agent",
                    message=f"Agent execution failed: {identifier}",
                    agent_id=agent_id,
                )

            raise
