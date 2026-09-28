"""Module containing workflow steps functionality for the Enterprise Agent Framework."""

from typing import Any

from src.exceptions import (
    ValidationError,
    exception_handler,
)
from src.observability import (
    log_event,
    span,
)
from src.runtime.crew_runtime import (
    CrewRuntime,
)
from workflows.workflow import (
    WorkflowStep,
)
from workflows.workflow_conditions import (
    evaluate_condition,
)
from workflows.workflow_context import (
    WorkflowContext,
)


class WorkflowStepExecutor:

    """WorkflowStepExecutor framework model or service class."""

    def __init__(
        self,
        crew_runtime: CrewRuntime,
    ):
        """Initialize the object with the supplied configuration."""
        self.crew_runtime = crew_runtime

    # ---------------------------------------------------------
    # EXECUTE STEP
    # ---------------------------------------------------------

    @exception_handler("workflow.step.execute")
    def execute(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> Any:
        """Execute a workflow step."""

        context.current_step = step.id

        log_event(
            "INFO",
            "workflow.step_started",
            component="workflow",
            message=f"Workflow step started: {step.id}",
            step_id=step.id,
            step_type=step.type,
        )

        try:

            with span(
                f"workflow.step.{step.id}",
                component="workflow",
                step_id=step.id,
                step_type=step.type,
            ):

                if step.type == "agent":

                    result = self._execute_agent(
                        step,
                        context,
                    )

                elif step.type == "condition":

                    result = self._execute_condition(
                        step,
                        context,
                    )

                elif step.type == "loop":

                    result = self._execute_loop(
                        step,
                        context,
                    )

                else:

                    raise ValidationError(
                        f"Unsupported workflow step type: "
                        f"{step.type}",
                        user_message=(
                            f"Unsupported workflow step type: "
                            f"{step.type}"
                        ),
                    )

            log_event(
                "INFO",
                "workflow.step_completed",
                component="workflow",
                message=(
                    f"Workflow step completed: {step.id}"
                ),
                step_id=step.id,
                step_type=step.type,
            )

            return result

        except Exception as exc:

            log_event(
                "ERROR",
                "workflow.step_failed",
                component="workflow",
                message=(
                    f"Workflow step failed: {step.id}"
                ),
                step_id=step.id,
                step_type=step.type,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            raise

    # ---------------------------------------------------------
    # AGENT
    # ---------------------------------------------------------

    def _execute_agent(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> Any:
        """Execute an agent workflow step."""

        if not step.agent:

            raise ValidationError(
                f"Agent step '{step.id}' "
                "must define an agent.",
                user_message=(
                    f"Agent step '{step.id}' "
                    "must define an agent."
                ),
            )

        result = self.crew_runtime.execute(
            identifier=step.agent,
            inputs={
                "user_input": context.user_input,
                "previous_output": context.latest_output(),
                "variables": context.variables,
            },
        )

        context.set_output(
            step.id,
            result,
        )

        return result

    # ---------------------------------------------------------
    # CONDITION
    # ---------------------------------------------------------

    def _execute_condition(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> str:
        """Execute a condition workflow step."""

        if not step.condition:

            raise ValidationError(
                f"Condition step '{step.id}' "
                "must define a condition.",
                user_message=(
                    f"Condition step '{step.id}' "
                    "must define a condition."
                ),
            )

        condition_context = {
            **context.variables,
            "user_input": context.user_input,
            "latest_output": context.latest_output(),
        }

        result = evaluate_condition(
            step.condition,
            condition_context,
        )

        if result:

            next_step = step.if_true

        else:

            next_step = step.if_false

        context.set_output(
            step.id,
            result,
        )

        return next_step

    # ---------------------------------------------------------
    # LOOP
    # ---------------------------------------------------------

    def _execute_loop(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> Any:
        """Execute a loop workflow step."""

        if not step.agent:

            raise ValidationError(
                f"Loop step '{step.id}' "
                "must define an agent.",
                user_message=(
                    f"Loop step '{step.id}' "
                    "must define an agent."
                ),
            )

        if not step.max_iterations:

            raise ValidationError(
                f"Loop step '{step.id}' "
                "must define max_iterations.",
                user_message=(
                    f"Loop step '{step.id}' "
                    "must define max_iterations."
                ),
            )

        results = []

        for iteration in range(
            step.max_iterations
        ):

            context.iteration = iteration + 1

            result = self.crew_runtime.execute(
                identifier=step.agent,
                inputs={
                    "user_input": context.user_input,
                    "previous_output": (
                        context.latest_output()
                    ),
                    "variables": context.variables,
                    "iteration": context.iteration,
                },
            )

            results.append(
                result
            )

            context.set_output(
                step.id,
                result,
            )

        return results