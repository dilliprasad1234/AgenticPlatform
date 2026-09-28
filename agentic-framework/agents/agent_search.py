"""Module containing agent search functionality."""

import typer

from agents.agent_execution import (
    execute_agent,
)
from agents.agent_options import (
    GOOD_AT_OPTIONS,
    PRACTICE_AREAS,
)
from agents.agent_registry import (
    AgentRegistry,
)
from src.cli.ui import (
    menu,
)
from src.exceptions import (
    ValidationError,
    exception_handler,
)
from src.runtime.crew_runtime import (
    CrewRuntime,
)


def _select_search_result(
    results,
    search_description: str,
):
    """Display search results and select an agent."""

    if not results:

        typer.echo(
            f"\nNo agents found for "
            f"{search_description}."
        )

        typer.echo()

        return None

    typer.echo(
        f"\nAgents matching "
        f"{search_description}:"
    )

    for index, agent in enumerate(
        results,
        start=1,
    ):

        typer.echo(
            f"{index}. {agent.agent.name}"
        )

    typer.echo()

    choice = typer.prompt(
        "Select an agent",
        type=int,
    )

    if (
        choice < 1
        or choice > len(results)
    ):
        raise ValidationError(
            "Invalid agent search result selection.",
            user_message=(
                "Invalid agent selection."
            ),
        )

    return results[choice - 1]


def _select_practice_area() -> str:
    """Select a practice area for agent search."""

    typer.echo("\nPractice Areas:")

    for index, practice_area in enumerate(
        PRACTICE_AREAS,
        start=1,
    ):
        typer.echo(
            f"{index}. {practice_area}"
        )

    choice = typer.prompt(
        "Select Practice Area",
        type=int,
    )

    if (
        choice < 1
        or choice > len(PRACTICE_AREAS)
    ):
        raise ValidationError(
            "Invalid practice area selection.",
            user_message="Invalid practice area selection.",
        )

    return PRACTICE_AREAS[choice - 1]


def _select_good_at() -> str:
    """Select a good at value for agent search."""

    typer.echo("\nGood At Options:")

    for index, good_at in enumerate(
        GOOD_AT_OPTIONS,
        start=1,
    ):
        typer.echo(
            f"{index}. {good_at}"
        )

    choice = typer.prompt(
        "Select Good At",
        type=int,
    )

    if (
        choice < 1
        or choice > len(GOOD_AT_OPTIONS)
    ):
        raise ValidationError(
            "Invalid good at selection.",
            user_message="Invalid good at selection.",
        )

    return GOOD_AT_OPTIONS[choice - 1]


@exception_handler("agent.search")
def search_agents(
    runtime: CrewRuntime,
    agents: AgentRegistry,
) -> None:
    """Display agent search options."""

    while True:

        menu(
            "Search Agents",
            [
                "1. Practice Area",
                "2. Good At",
                "3. Keyword",
                "4. Back",
            ],
        )

        choice = typer.prompt(
            "Select an option"
        ).strip()

        # -----------------------------------------
        # Practice Area
        # -----------------------------------------

        if choice == "1":

            selected_area = (
                _select_practice_area()
            )

            results = agents.search_agents(
                practice_area=selected_area
            )

            selected_agent = _select_search_result(
                results,
                f"practice area '{selected_area}'",
            )

            if selected_agent is not None:

                execute_agent(
                    runtime,
                    agents,
                    agent=selected_agent,
                )

        # -----------------------------------------
        # Good At
        # -----------------------------------------

        elif choice == "2":

            selected_good_at = (
                _select_good_at()
            )

            results = agents.search_agents(
                good_at=selected_good_at
            )

            selected_agent = _select_search_result(
                results,
                f"good at '{selected_good_at}'",
            )

            if selected_agent is not None:

                execute_agent(
                    runtime,
                    agents,
                    agent=selected_agent,
                )

        # -----------------------------------------
        # Keyword
        # -----------------------------------------

        elif choice == "3":

            keyword = typer.prompt(
                "Enter keyword"
            ).strip()

            if not keyword:

                raise ValidationError(
                    "Agent search keyword cannot be empty.",
                    user_message=(
                        "Keyword cannot be empty."
                    ),
                )

            results = agents.search_agents(
                keyword=keyword
            )

            selected_agent = _select_search_result(
                results,
                f"keyword '{keyword}'",
            )

            if selected_agent is not None:

                execute_agent(
                    runtime,
                    agents,
                    agent=selected_agent,
                )

        # -----------------------------------------
        # Back
        # -----------------------------------------

        elif choice == "4":

            return

        # -----------------------------------------
        # Invalid Selection
        # -----------------------------------------

        else:

            raise ValidationError(
                "Invalid agent search selection.",
                user_message=(
                    "Please select 1, 2, 3, or 4."
                ),
            )