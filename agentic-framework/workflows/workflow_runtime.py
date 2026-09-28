"""Module containing workflow runtime functionality for the Enterprise Agent Framework."""

from datetime import datetime
from typing import Any

from crewai import (
    Crew,
    Process,
    Task,
)

from agents.agent_registry import (
    AgentRegistry,
)
from src.exceptions import (
    ValidationError,
    WorkflowError,
    exception_handler,
)
from src.observability import (
    end_run,
    log_event,
    span,
    start_run,
)
from src.runtime.crew_runtime import (
    CrewRuntime,
)
from tools.tool_registry import (
    ToolRegistry,
)
from workflows.workflow_context import (
    WorkflowContext,
)
from workflows.workflow_execution_log import (
    WorkflowExecutionLogger,
)
from workflows.workflow_registry import (
    WorkflowRegistry,
)
from workflows.workflow_steps import (
    WorkflowStepExecutor,
)


class WorkflowRuntime:

    """WorkflowRuntime framework model or service class."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        workflow_registry: WorkflowRegistry,
        tool_registry: ToolRegistry,
    ):
        """Initialize the object with the supplied configuration."""

        self.agent_registry = agent_registry
        self.workflow_registry = workflow_registry

        self.crew_runtime = CrewRuntime(
            agent_registry,
            tool_registry,
        )

        self.step_executor = WorkflowStepExecutor(
            self.crew_runtime
        )

        # Logger is created per workflow execution
        self.logger = None

    # =========================================================
    # MAIN EXECUTION
    # =========================================================
    @exception_handler("workflow.runtime.execute")
    def execute(
        self,
        workflow_id: str,
        user_input: str = "",
    ) -> Any:
        """Execute a workflow."""
        if not user_input or not user_input.strip():
            user_input = "Execute the workflow using default parameters."

        workflow = self.workflow_registry.get(
            workflow_id
        )

        # The workflow owns the top-level execution trace.
        # All nested agents and tools reuse this trace
        # for debugging correlation.
        start_run(
            run_type="workflow_runtime",
            name=workflow_id,
            workflow_id=workflow_id,
            workflow_name=workflow.name,
        )

        log_event(
            "INFO",
            "workflow.execution_started",
            component="workflow",
            message=(
                f"Workflow execution started: "
                f"{workflow_id}"
            ),
            workflow_id=workflow_id,
            workflow_name=workflow.name,
        )

        # -----------------------------------------------------
        # Create logger for this workflow execution
        # -----------------------------------------------------

        logger = WorkflowExecutionLogger(
            workflow_id
        )
        self.logger = logger
        logger.start_capture()

        try:
            # -------------------------------------------------
            # Execution Started
            # -------------------------------------------------

            print("\n" + "=" * 70)
            print("WORKFLOW EXECUTION STARTED")
            print("=" * 70)
            print(
                f"Workflow ID : {workflow_id}"
            )
            print(
                f"Workflow    : {workflow.name}"
            )
            print(
                f"Execution Type : "
                f"{workflow.execution.type if workflow.execution else 'sequential'}"
            )
            print("=" * 70)

            # TEST ONLY
            #raise RuntimeError("TEST: Workflow execution failure")

            # -------------------------------------------------
            # Execute Workflow
            # -------------------------------------------------

            if (
                workflow.execution is not None
                and workflow.execution.type == "graph"
            ):

                with span(
                    "workflow.graph_execute",
                    component="workflow",
                    workflow_id=workflow_id,
                ):

                    result = self._execute_graph(
                        workflow,
                        user_input,
                    )

            else:

                with span(
                    "workflow.sequential_execute",
                    component="workflow",
                    workflow_id=workflow_id,
                ):

                    result = self._execute_sequential(
                        workflow,
                        user_input,
                    )

            # -------------------------------------------------
            # Workflow Completed
            # -------------------------------------------------

            print("\n" + "=" * 70)
            print("WORKFLOW EXECUTION COMPLETED")
            print("=" * 70)

            print(
                f"Completed At : "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            print(
                f"Log File     : {logger.path}"
            )
            print("=" * 70)

            log_event(
                "INFO",
                "workflow.execution_completed",
                component="workflow",
                message=(
                    f"Workflow execution completed: "
                    f"{workflow_id}"
                ),
                workflow_id=workflow_id,
            )

            end_run(
                status="success",
                run_type="workflow_runtime",
                workflow_id=workflow_id,
            )

            return result

        # -----------------------------------------------------
        # Workflow Failed
        # -----------------------------------------------------

        except Exception as exc:

            print("\n" + "=" * 70)
            print("WORKFLOW EXECUTION FAILED")
            print("=" * 70)

            print(
                f"Error Type : {type(exc).__name__}"
            )

            print(
                f"Error      : {exc}"
            )

            print(
                f"Failed At  : "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            print("=" * 70)

            end_run(
                status="failed",
                run_type="workflow_runtime",
                workflow_id=workflow_id,
            )

            raise

        # -----------------------------------------------------
        # Always stop log capture
        # -----------------------------------------------------

        finally:

            logger.stop_capture()

    # =========================================================
    # SEQUENTIAL EXECUTION
    # =========================================================

    def _execute_sequential(
        self,
        workflow,
        user_input: str,
    ) -> Any:
        """Execute a sequential workflow."""

        agents = []
        tasks = []

        for index, agent_id in enumerate(
            workflow.agents
        ):

            agent = self.crew_runtime.build_agent(
                agent_id
            )

            agents.append(
                agent
            )

            task = self._build_task(
                workflow,
                agent_id,
                agent,
                index,
                user_input,
                tasks,
            )

            tasks.append(
                task
            )

        self._log(
            "\n"
            + "=" * 70
        )

        self._log(
            "SEQUENTIAL CREW EXECUTION"
        )

        self._log(
            "=" * 70
        )

        self._log(
            f"Agents: {workflow.agents}"
        )

        result = self._execute_crew(
            agents,
            tasks,
        )

        # Apply the same configured output guardrails used by standalone
        # agent execution to each sequential workflow task. This keeps the
        # workflow path from bypassing guardrails merely because CrewAI is
        # executing multiple agents in one Crew.
        task_outputs = getattr(result, "tasks_output", None) or []
        for index, task_output in enumerate(task_outputs):
            if index >= len(workflow.agents):
                break
            agent_id = workflow.agents[index]
            agent_spec = self.crew_runtime.agent_runtime.load_agent(agent_id)
            normalized = self.crew_runtime._normalize_output(task_output)
            self.crew_runtime._validate_output(agent_spec, normalized)

        # The final Crew result is normally the recommendation agent's output.
        # Validate it as well because some CrewAI versions do not expose
        # tasks_output consistently.
        final_agent_spec = self.crew_runtime.agent_runtime.load_agent(workflow.agents[-1])
        normalized_final = self.crew_runtime._normalize_output(result)
        self.crew_runtime._validate_output(final_agent_spec, normalized_final)

        return normalized_final

    # =========================================================
    # GRAPH EXECUTION
    # =========================================================

    def _execute_graph(
        self,
        workflow,
        user_input: str,
    ) -> Any:
        """Execute a graph workflow."""

        execution = workflow.execution

        if execution is None:

            raise ValidationError(
                "Workflow execution configuration is missing.",
                user_message=(
                    "Workflow execution configuration is missing."
                ),
            )

        if not execution.steps:

            raise ValidationError(
                f"Graph workflow '{workflow.name}' "
                "does not contain any steps.",
                user_message=(
                    f"Graph workflow '{workflow.name}' "
                    "does not contain any steps."
                ),
            )

        # -----------------------------------------------------
        # Create step lookup
        # -----------------------------------------------------

        steps = {
            step.id: step
            for step in execution.steps
        }

        # -----------------------------------------------------
        # Validate duplicate IDs
        # -----------------------------------------------------

        if len(steps) != len(
            execution.steps
        ):

            raise ValidationError(
                "Workflow contains duplicate step IDs.",
                user_message=(
                    "Workflow contains duplicate step IDs."
                ),
            )

        # -----------------------------------------------------
        # Validate references
        # -----------------------------------------------------

        self._validate_graph(
            execution.steps,
            steps,
        )

        # -----------------------------------------------------
        # Starting step
        # -----------------------------------------------------

        current_step = execution.steps[0]

        context = WorkflowContext(
            user_input
        )

        result = None

        # -----------------------------------------------------
        # Safety limit
        # -----------------------------------------------------

        max_step_executions = 100

        step_count = 0

        self._log(
            "\n"
            + "=" * 70
        )

        self._log(
            "GRAPH / ORCHESTRATION EXECUTION"
        )

        self._log(
            "=" * 70
        )

        self._log(
            f"Starting Step : {current_step.id}"
        )

        # -----------------------------------------------------
        # Execute graph
        # -----------------------------------------------------

        while current_step is not None:

            step_count += 1

            if step_count > max_step_executions:

                raise WorkflowError(
                    "Workflow exceeded the maximum number of step executions (possible infinite loop).",
                    workflow_name=workflow.name,
                    step=current_step,
                    details={
                        "max_step_executions": max_step_executions,
                        "step_count": step_count,
                    },
                )

            # -------------------------------------------------
            # Execute current step
            # -------------------------------------------------

            result = self.step_executor.execute(
                current_step,
                context,
            )

            # -------------------------------------------------
            # Determine next step
            # -------------------------------------------------

            next_step_id = self._get_next_step(
                current_step,
                result,
            )

            # -------------------------------------------------
            # Log execution
            # -------------------------------------------------

            self._log_step(
                current_step,
                result,
                next_step_id,
                step_count,
            )

            # -------------------------------------------------
            # Workflow completed
            # -------------------------------------------------

            if next_step_id is None:

                break

            # -------------------------------------------------
            # Validate next step
            # -------------------------------------------------

            if next_step_id not in steps:

                raise ValidationError(
                    f"Workflow step "
                    f"'{current_step.id}' references "
                    f"unknown step "
                    f"'{next_step_id}'.",
                    user_message=(
                        f"Workflow step "
                        f"'{current_step.id}' references "
                        f"unknown step "
                        f"'{next_step_id}'."
                    ),
                )

            current_step = steps[
                next_step_id
            ]

        self._log(
            "\n"
            + "=" * 70
        )

        self._log(
            "GRAPH EXECUTION FINISHED"
        )

        self._log(
            f"Total Step Executions: "
            f"{step_count}"
        )

        self._log(
            "=" * 70
        )

        return result

    # =========================================================
    # GRAPH VALIDATION
    # =========================================================

    def _validate_graph(
        self,
        steps,
        step_lookup,
    ) -> None:
        """Validate graph configuration."""

        for step in steps:

            # -------------------------------------------------
            # Agent
            # -------------------------------------------------

            if step.type == "agent":

                if not step.agent:

                    raise ValidationError(
                        f"Agent step '{step.id}' "
                        "must define an agent.",
                        user_message=(
                            f"Agent step '{step.id}' "
                            "must define an agent."
                        ),
                    )

                available_agents = (
                    self.agent_registry.list_agents()
                )

                available_agent_ids = [
                    agent.id
                    for agent in available_agents
                ]

                if step.agent not in available_agent_ids:

                    raise ValidationError(
                        f"Step '{step.id}' references "
                        f"unknown agent "
                        f"'{step.agent}'.",
                        user_message=(
                            f"Step '{step.id}' references "
                            f"unknown agent "
                            f"'{step.agent}'."
                        ),
                    )

            # -------------------------------------------------
            # Condition
            # -------------------------------------------------

            elif step.type == "condition":

                if not step.condition:

                    raise ValidationError(
                        f"Condition step "
                        f"'{step.id}' "
                        "must define a condition.",
                        user_message=(
                            f"Condition step "
                            f"'{step.id}' "
                            "must define a condition."
                        ),
                    )

                if not step.if_false:

                    raise ValidationError(
                        f"Condition step "
                        f"'{step.id}' "
                        "must define if_false.",
                        user_message=(
                            f"Condition step "
                            f"'{step.id}' "
                            "must define if_false."
                        ),
                    )

            # -------------------------------------------------
            # Loop
            # -------------------------------------------------

            elif step.type == "loop":

                if not step.max_iterations:

                    raise ValidationError(
                        f"Loop step "
                        f"'{step.id}' "
                        "must define max_iterations.",
                        user_message=(
                            f"Loop step "
                            f"'{step.id}' "
                            "must define max_iterations."
                        ),
                    )

            # -------------------------------------------------
            # Validate next
            # -------------------------------------------------

            if step.next:

                if step.next not in step_lookup:

                    raise ValidationError(
                        f"Step '{step.id}' "
                        f"references unknown next "
                        f"step '{step.next}'.",
                        user_message=(
                            f"Step '{step.id}' "
                            f"references unknown next "
                            f"step '{step.next}'."
                        ),
                    )

            # -------------------------------------------------
            # Validate condition branches
            # -------------------------------------------------

            if step.type == "condition":

                if (
                    step.if_true is not None
                    and step.if_true not in step_lookup
                ):

                    raise ValidationError(
                        f"Condition step "
                        f"'{step.id}' "
                        f"references unknown "
                        f"if_true step "
                        f"'{step.if_true}'.",
                        user_message=(
                            f"Condition step "
                            f"'{step.id}' "
                            f"references unknown "
                            f"if_true step "
                            f"'{step.if_true}'."
                        ),
                    )

                if (
                    step.if_false is not None
                    and step.if_false not in step_lookup
                ):

                    raise ValidationError(
                        f"Condition step "
                        f"'{step.id}' "
                        f"references unknown "
                        f"if_false step "
                        f"'{step.if_false}'.",
                        user_message=(
                            f"Condition step "
                            f"'{step.id}' "
                            f"references unknown "
                            f"if_false step "
                            f"'{step.if_false}'."
                        ),
                    )

    # =========================================================
    # DETERMINE NEXT STEP
    # =========================================================

    def _get_next_step(
        self,
        step,
        result,
    ) -> str | None:
        """Determine the next workflow step."""

        # -----------------------------------------------------
        # Condition
        # -----------------------------------------------------

        if step.type == "condition":

            return result

        # -----------------------------------------------------
        # Agent / Loop
        # -----------------------------------------------------

        return step.next

    # =========================================================
    # BUILD LEGACY SEQUENTIAL TASK
    # =========================================================

    def _build_task(
        self,
        workflow,
        agent_id: str,
        agent,
        index: int,
        user_input: str,
        previous_tasks: list,
    ):
        """Build a legacy sequential task."""

        agent_spec = self.agent_registry.get(
            agent_id
        )

        description = (
            f"{agent_spec.behaviour.description}\n\n"
            f"Workflow: {workflow.name}\n"
            f"Workflow Description: "
            f"{workflow.description}\n\n"
            f"Practice Area: "
            f"{workflow.practice_area}\n\n"
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
            description += (
                "Agent Guidelines and Instructions:\n"
                + "\n".join(prompt_rules)
                + "\n\n"
            )

        if index == 0:

            description += (
                "Analyze the following "
                "workflow input:\n\n"
                f"{user_input}"
            )

            context = None

        else:

            description += (
                "Analyze and process the output "
                "from the previous workflow agent."
            )

            context = previous_tasks[-1:]

        return Task(
            description=description,
            expected_output=(
                agent_spec.behaviour.expected_output
            ),
            agent=agent,
            context=context,
        )

    # =========================================================
    # STEP LOGGER
    # =========================================================

    def _log_step(
        self,
        step,
        result=None,
        next_step_id=None,
        step_count=None,
    ):
        """Log workflow step execution."""

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self._log(
            "\n"
            + "=" * 70
        )

        self._log(
            f"[{timestamp}] WORKFLOW STEP"
        )

        self._log(
            "=" * 70
        )

        self._log(
            f"Execution Count : {step_count}"
        )

        self._log(
            f"Step ID         : {step.id}"
        )

        self._log(
            f"Step Type       : {step.type}"
        )

        # -----------------------------------------------------
        # Agent
        # -----------------------------------------------------

        if step.type == "agent":

            self._log(
                f"Agent           : "
                f"{step.agent}"
            )

        # -----------------------------------------------------
        # Condition
        # -----------------------------------------------------

        if step.type == "condition":

            self._log(
                f"Condition       : "
                f"{step.condition}"
            )

            self._log(
                f"If TRUE         : "
                f"{step.if_true}"
            )

            self._log(
                f"If FALSE        : "
                f"{step.if_false}"
            )

        # -----------------------------------------------------
        # Loop
        # -----------------------------------------------------

        if step.type == "loop":

            self._log(
                f"Max Iterations  : "
                f"{step.max_iterations}"
            )

        self._log(
            "-" * 70
        )

        # -----------------------------------------------------
        # Result
        # -----------------------------------------------------

        if result is not None:

            self._log(
                "Result:"
            )

            self._log(
                str(result)
            )

        else:

            self._log(
                "Result: None"
            )

        self._log(
            "-" * 70
        )

        # -----------------------------------------------------
        # Next Step
        # -----------------------------------------------------

        if next_step_id:

            self._log(
                f"Next Step       : "
                f"{next_step_id}"
            )

        else:

            self._log(
                "Next Step       : "
                "WORKFLOW COMPLETED"
            )

        self._log(
            "=" * 70
        )

    # =========================================================
    # LOGGER HELPER
    # =========================================================

    def _log(
        self,
        message: str,
    ) -> None:
        """Write a workflow execution log message."""

        if self.logger is not None:

            self.logger.log(
                message
            )

        else:

            print(message)

    # =========================================================
    # CREW EXECUTION
    # =========================================================

    def _execute_crew(
        self,
        agents,
        tasks,
    ):
        """Execute the CrewAI workflow."""

        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        return crew.kickoff()