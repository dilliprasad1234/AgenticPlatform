"""Module containing workflow builder functionality for the Enterprise Agent Framework."""

import typer

from agents.agent_registry import (
    AgentRegistry,
)
from src.cli.ui import (
    info,
)
from src.exceptions import (
    ValidationError,
    exception_handler,
)
from workflows.workflow import (
    WorkflowExecution,
    WorkflowStep,
)


class WorkflowBuilder:
    """
    Interactive builder for workflow execution plans.

    Supports:

        - Sequential workflows
        - Graph/orchestrated workflows
        - Agent steps
        - Condition steps
        - Loop steps
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
    ):
        """Initialize the object with the supplied configuration."""
        self.agent_registry = agent_registry

    # =========================================================
    # PUBLIC
    # =========================================================

    @exception_handler("workflow.builder.build")
    def build(self) -> WorkflowExecution:
        """Build a workflow execution plan."""

        typer.echo(
            "\nExecution Type:"
        )

        typer.echo(
            "1. Sequential"
        )

        typer.echo(
            "2. Graph / Orchestration"
        )

        choice = typer.prompt(
            "Select execution type",
            type=int,
        )

        if choice == 1:

            return self._build_sequential()

        if choice == 2:

            return self._build_graph()

        raise ValidationError(
            "Invalid execution type.",
            user_message=(
                "Invalid execution type."
            ),
        )

    # =========================================================
    # SEQUENTIAL
    # =========================================================

    def _build_sequential(
        self,
    ) -> WorkflowExecution:
        """Build a sequential workflow."""

        available_agents = (
            self.agent_registry.list_agents()
        )

        if not available_agents:

            raise ValidationError(
                "No agents found. "
                "Create at least one agent first.",
                user_message=(
                    "No agents found. "
                    "Create at least one agent first."
                ),
            )

        typer.echo(
            "\nAvailable Agents:"
        )

        for index, agent in enumerate(
            available_agents,
            start=1,
        ):

            typer.echo(
                f"{index}. {agent.agent.name}"
            )

        typer.echo()

        count = typer.prompt(
            "Number of agents in sequence",
            type=int,
        )

        if count < 1:

            raise ValidationError(
                "Number of agents must be at least 1.",
                user_message=(
                    "Number of agents must be at least 1."
                ),
            )

        steps = []

        for index in range(count):

            choice = typer.prompt(
                f"{index + 1}. Select Agent",
                type=int,
            )

            if (
                choice < 1
                or choice > len(available_agents)
            ):

                raise ValidationError(
                    "Invalid agent selection.",
                    user_message=(
                        "Invalid agent selection."
                    ),
                )

            selected_agent = available_agents[
                choice - 1
            ]

            step_id = typer.prompt(
                f"Step {index + 1} ID",
                default=(
                    f"step_{index + 1}"
                ),
            )

            next_step = None

            if index < count - 1:

                next_step = (
                    f"step_{index + 2}"
                )

            steps.append(
                WorkflowStep(
                    id=step_id,
                    type="agent",
                    agent=selected_agent.id,
                    next=next_step,
                )
            )

        return WorkflowExecution(
            type="sequential",
            steps=steps,
        )

    # =========================================================
    # GRAPH
    # =========================================================

    def _build_graph(
        self,
    ) -> WorkflowExecution:
        """Build a graph workflow."""

        steps = []

        typer.echo(
            "\nBuild Workflow Graph"
        )

        typer.echo(
            "You can add Agent, Condition, "
            "or Loop steps."
        )

        typer.echo(
            "Type 'done' when finished."
        )

        while True:

            typer.echo(
                "\nStep Types:"
            )

            typer.echo(
                "1. Agent"
            )

            typer.echo(
                "2. Condition"
            )

            typer.echo(
                "3. Loop"
            )

            typer.echo(
                "4. Finish"
            )

            choice = typer.prompt(
                "Select step type"
            ).strip()

            if choice == "1":

                step = self._build_agent_step()

            elif choice == "2":

                step = self._build_condition_step()

            elif choice == "3":

                step = self._build_loop_step()

            elif choice == "4":

                break

            else:

                raise ValidationError(
                    "Invalid step type.",
                    user_message=(
                        "Invalid step type."
                    ),
                )

            steps.append(
                step
            )

            info(
                f"Step '{step.id}' added."
            )

        if not steps:

            raise ValidationError(
                "Workflow must contain at least one step.",
                user_message=(
                    "Workflow must contain at least one step."
                ),
            )

        self._validate_graph(
            steps
        )

        return WorkflowExecution(
            type="graph",
            steps=steps,
        )

    # =========================================================
    # AGENT STEP
    # =========================================================

    def _build_agent_step(
        self,
    ) -> WorkflowStep:
        """Build an agent step."""

        available_agents = (
            self.agent_registry.list_agents()
        )

        if not available_agents:

            raise ValidationError(
                "No agents found.",
                user_message=(
                    "No agents found."
                ),
            )

        typer.echo(
            "\nAvailable Agents:"
        )

        for index, agent in enumerate(
            available_agents,
            start=1,
        ):

            typer.echo(
                f"{index}. {agent.agent.name}"
            )

        typer.echo()

        step_id = typer.prompt(
            "Step ID"
        ).strip()

        if not step_id:

            raise ValidationError(
                "Step ID cannot be empty.",
                user_message=(
                    "Step ID cannot be empty."
                ),
            )

        choice = typer.prompt(
            "Select Agent",
            type=int,
        )

        if (
            choice < 1
            or choice > len(available_agents)
        ):

            raise ValidationError(
                "Invalid agent selection.",
                user_message=(
                    "Invalid agent selection."
                ),
            )

        selected_agent = available_agents[
            choice - 1
        ]

        next_step = typer.prompt(
            "Next Step ID",
            default="",
        ).strip()

        return WorkflowStep(
            id=step_id,
            type="agent",
            agent=selected_agent.id,
            next=next_step or None,
        )

    # =========================================================
    # CONDITION STEP
    # =========================================================

    def _build_condition_step(
        self,
    ) -> WorkflowStep:
        """Build a condition step."""

        step_id = typer.prompt(
            "Condition Step ID"
        ).strip()

        if not step_id:

            raise ValidationError(
                "Step ID cannot be empty.",
                user_message=(
                    "Step ID cannot be empty."
                ),
            )

        condition = typer.prompt(
            "Condition"
        ).strip()

        if not condition:

            raise ValidationError(
                "Condition cannot be empty.",
                user_message=(
                    "Condition cannot be empty."
                ),
            )

        typer.echo(
            "\nExample:"
        )

        typer.echo(
            "latest_output contains approved"
        )

        if_true = typer.prompt(
            "If TRUE -> Step ID",
            default="",
        ).strip()

        if_true = if_true or None

        if_false = typer.prompt(
            "If FALSE -> Step ID"
        ).strip()

        if not if_false:

            raise ValidationError(
                "FALSE branch cannot be empty.",
                user_message=(
                    "FALSE branch cannot be empty."
                ),
            )

        return WorkflowStep(
            id=step_id,
            type="condition",
            condition=condition,
            if_true=if_true,
            if_false=if_false,
        )

    # =========================================================
    # LOOP STEP
    # =========================================================

    def _build_loop_step(
        self,
    ) -> WorkflowStep:
        """Build a loop step."""

        step_id = typer.prompt(
            "Loop Step ID"
        ).strip()

        if not step_id:

            raise ValidationError(
                "Step ID cannot be empty.",
                user_message=(
                    "Step ID cannot be empty."
                ),
            )

        available_agents = (
            self.agent_registry.list_agents()
        )

        if not available_agents:

            raise ValidationError(
                "No agents found.",
                user_message=(
                    "No agents found."
                ),
            )

        typer.echo(
            "\nAvailable Agents:"
        )

        for index, agent in enumerate(
            available_agents,
            start=1,
        ):

            typer.echo(
                f"{index}. {agent.agent.name}"
            )

        typer.echo()

        choice = typer.prompt(
            "Select Agent for Loop",
            type=int,
        )

        if (
            choice < 1
            or choice > len(available_agents)
        ):

            raise ValidationError(
                "Invalid agent selection.",
                user_message=(
                    "Invalid agent selection."
                ),
            )

        selected_agent = available_agents[
            choice - 1
        ]

        next_step = typer.prompt(
            "Next Step ID after loop"
        ).strip()

        if not next_step:

            raise ValidationError(
                "Next Step ID cannot be empty.",
                user_message=(
                    "Next Step ID cannot be empty."
                ),
            )

        max_iterations = typer.prompt(
            "Maximum iterations",
            type=int,
            default=3,
        )

        if max_iterations < 1:

            raise ValidationError(
                "Maximum iterations must be at least 1.",
                user_message=(
                    "Maximum iterations must be at least 1."
                ),
            )

        return WorkflowStep(
            id=step_id,
            type="loop",
            agent=selected_agent.id,
            next=next_step,
            max_iterations=max_iterations,
        )

    # =========================================================
    # GRAPH VALIDATION
    # =========================================================

    def _validate_graph(
        self,
        steps: list[WorkflowStep],
    ) -> None:
        """Validate workflow graph configuration."""

        step_ids = {
            step.id
            for step in steps
        }

        if len(step_ids) != len(steps):

            raise ValidationError(
                "Duplicate workflow step IDs are not allowed.",
                user_message=(
                    "Duplicate workflow step IDs are not allowed."
                ),
            )

        for step in steps:

            if step.type == "agent":

                if not step.agent:

                    raise ValidationError(
                        f"Agent step '{step.id}' "
                        "must specify an agent.",
                        user_message=(
                            f"Agent step '{step.id}' "
                            "must specify an agent."
                        ),
                    )

                if (
                    step.next
                    and step.next not in step_ids
                ):

                    raise ValidationError(
                        f"Step '{step.id}' references "
                        f"unknown next step '{step.next}'.",
                        user_message=(
                            f"Step '{step.id}' references "
                            f"unknown next step '{step.next}'."
                        ),
                    )

            elif step.type == "condition":

                if not step.condition:

                    raise ValidationError(
                        f"Condition step '{step.id}' "
                        "must specify a condition.",
                        user_message=(
                            f"Condition step '{step.id}' "
                            "must specify a condition."
                        ),
                    )

                if (
                    step.if_true is not None
                    and step.if_true not in step_ids
                ):

                    raise ValidationError(
                        f"Condition step '{step.id}' "
                        f"references unknown TRUE step "
                        f"'{step.if_true}'.",
                        user_message=(
                            f"Condition step '{step.id}' "
                            f"references unknown TRUE step "
                            f"'{step.if_true}'."
                        ),
                    )

                if (
                    step.if_false is not None
                    and step.if_false not in step_ids
                ):

                    raise ValidationError(
                        f"Condition step '{step.id}' "
                        f"references unknown FALSE step "
                        f"'{step.if_false}'.",
                        user_message=(
                            f"Condition step '{step.id}' "
                            f"references unknown FALSE step "
                            f"'{step.if_false}'."
                        ),
                    )

                if step.if_false not in step_ids:

                    raise ValidationError(
                        f"Condition step '{step.id}' "
                        f"references unknown FALSE step "
                        f"'{step.if_false}'.",
                        user_message=(
                            f"Condition step '{step.id}' "
                            f"references unknown FALSE step "
                            f"'{step.if_false}'."
                        ),
                    )

            elif step.type == "loop":

                if not step.agent:

                    raise ValidationError(
                        f"Loop step '{step.id}' "
                        "must specify an agent.",
                        user_message=(
                            f"Loop step '{step.id}' "
                            "must specify an agent."
                        ),
                    )

                if not step.max_iterations:

                    raise ValidationError(
                        f"Loop step '{step.id}' "
                        "must specify max_iterations.",
                        user_message=(
                            f"Loop step '{step.id}' "
                            "must specify max_iterations."
                        ),
                    )

                if (
                    step.next
                    and step.next not in step_ids
                ):

                    raise ValidationError(
                        f"Loop step '{step.id}' "
                        f"references unknown step "
                        f"'{step.next}'.",
                        user_message=(
                            f"Loop step '{step.id}' "
                            f"references unknown step "
                            f"'{step.next}'."
                        ),
                    )