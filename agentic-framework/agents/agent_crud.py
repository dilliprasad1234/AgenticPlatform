"""Module containing agent CRUD functionality for the Enterprise Agent Framework."""

import typer

from agents.agent_factory import AgentFactory
from agents.agent_registry import AgentRegistry
from guardrails.guardrail_selection import (
    select_guardrails,
)
from kb.kb_selection import (
    select_kbs,
)
from src.cli.ui import (
    info,
    success,
)
from src.exceptions import (
    ValidationError,
    exception_handler,
)
from src.llm.llm_configuration import (
    get_model_for_provider,
    select_llm_provider,
)
from src.utils.editor import (
    open_in_editor,
)
from tools.tool_registry import (
    ToolRegistry,
)
from tools.tool_selection import (
    select_tools,
    select_tools_for_edit,
)


@exception_handler("agent.create")
def create_agent(
    factory: AgentFactory,
    registry: AgentRegistry,
    tool_registry: ToolRegistry,
) -> None:
    """
    Create a new agent specification.
    """

    # -----------------------------------------
    # Agent Requirement
    # -----------------------------------------

    requirement = typer.prompt(
        "Describe what the agent should do"
    )

    if not requirement.strip():
        raise ValidationError(
            "Agent description cannot be empty.",
            user_message=(
                "Agent description cannot be empty."
            ),
        )

    # -----------------------------------------
    # Generate Agent Specification
    # -----------------------------------------

    info(
        "Generating AgentSpec..."
    )

    spec = factory.generate(
        requirement
    )

    # -----------------------------------------
    # LLM Configuration
    # -----------------------------------------

    provider = select_llm_provider()

    model = get_model_for_provider(
        provider
    )

    spec.llm_configuration.provider = provider
    spec.llm_configuration.model = model

    # -----------------------------------------
    # Tools
    # -----------------------------------------

    selected_tools = select_tools(
        tool_registry
    )

    spec.tools = selected_tools

    # -----------------------------------------
    # Knowledge Base
    # -----------------------------------------

    selected_kbs = select_kbs()

    spec.kb = selected_kbs

    # -----------------------------------------
    # Guardrails
    # -----------------------------------------

    selected_guardrails = select_guardrails()

    spec.guardrails = selected_guardrails

    # -----------------------------------------
    # Save
    # -----------------------------------------

    path = registry.save(
        spec
    )

    success(
        f"Agent created: {path}"
    )

    # -----------------------------------------
    # Open Editor
    # -----------------------------------------

    if open_in_editor(path):
        info(
            "Agent file opened in editor."
        )

    else:
        info(
            f"Edit manually: {path}"
        )


@exception_handler("agent.list")
def list_agents(
    registry: AgentRegistry,
):
    """
    List all available agents.
    """

    agents = registry.list_agents()

    if not agents:
        info(
            "No agents found."
        )
        return []

    typer.echo(
        "\nAvailable Agents:"
    )

    for index, agent in enumerate(
        agents,
        start=1,
    ):
        typer.echo(
            f"{index}. {agent.agent.name}"
        )

    typer.echo()

    return agents


def select_agent(
    registry: AgentRegistry,
):
    """
    Display available agents and return the selected agent.
    """

    agents = list_agents(
        registry
    )

    if not agents:
        return None

    choice = typer.prompt(
        "Select an agent",
        type=int,
    )

    if (
        choice < 1
        or choice > len(agents)
    ):
        raise ValidationError(
            f"Invalid agent selection: {choice}.",
            user_message="Invalid agent selection.",
        )

    return agents[
        choice - 1
    ]


@exception_handler("agent.edit")
def edit_agent(
    registry: AgentRegistry,
    tool_registry: ToolRegistry,
) -> None:
    """
    Edit an existing agent specification.
    """

    # -----------------------------------------
    # Select Agent
    # -----------------------------------------

    agent = select_agent(
        registry
    )

    if agent is None:
        return

    # -----------------------------------------
    # LLM Configuration
    # -----------------------------------------

    provider = select_llm_provider()

    model = get_model_for_provider(
        provider
    )

    agent.llm_configuration.provider = provider
    agent.llm_configuration.model = model

    # -----------------------------------------
    # Tools
    # -----------------------------------------

    selected_tools = select_tools_for_edit(
        tool_registry,
        current_tools=agent.tools,
    )

    agent.tools = selected_tools

    # -----------------------------------------
    # Knowledge Base
    # -----------------------------------------

    selected_kbs = select_kbs()

    agent.kb = selected_kbs

    # -----------------------------------------
    # Guardrails
    # -----------------------------------------

    selected_guardrails = select_guardrails()

    agent.guardrails = selected_guardrails

    # -----------------------------------------
    # Save
    # -----------------------------------------

    path = registry.save(
        agent
    )

    success(
        f"Agent updated: {path}"
    )

    # -----------------------------------------
    # Open Editor
    # -----------------------------------------

    if open_in_editor(path):
        info(
            "Agent file opened in editor."
        )

    else:
        info(
            f"Edit manually: {path}"
        )


@exception_handler("agent.delete")
def delete_agent(
    registry: AgentRegistry,
) -> None:
    """
    Delete an existing agent specification.
    """

    # -----------------------------------------
    # Select Agent
    # -----------------------------------------

    agent = select_agent(
        registry
    )

    if agent is None:
        return

    # -----------------------------------------
    # Resolve Path
    # -----------------------------------------

    path = registry.path_for(
        agent.id
    )

    # -----------------------------------------
    # Confirmation
    # -----------------------------------------

    if not typer.confirm(
        f"Delete '{agent.agent.name}'?"
    ):
        info(
            "Deletion cancelled."
        )
        return

    # -----------------------------------------
    # Delete
    # -----------------------------------------

    registry.delete(
        agent.id
    )

    success(
        f"Agent deleted successfully: {path.name}"
    )