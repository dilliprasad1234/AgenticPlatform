"""Module containing agent registry functionality for the Enterprise Agent Framework."""

from pathlib import Path

import yaml

from agents.agent import AgentSpec
from src.exceptions import (
    ArtifactNotFoundError,
    ValidationError,
    exception_handler,
)
from src.utils.yaml_loader import load_yaml_model


class AgentRegistry:
    """Registry responsible for storing and retrieving agent specifications."""

    def __init__(
        self,
        directory: Path,
    ):
        """Initialize the agent registry."""

        self.directory = directory

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    @exception_handler("agent.registry.save")
    def save(
        self,
        spec: AgentSpec,
    ) -> Path:
        """
        Save an AgentSpec as a YAML definition.
        """

        path = (
            self.directory
            / f"{spec.id}.yaml"
        )

        path.write_text(
            yaml.safe_dump(
                spec.model_dump(),
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

        return path

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------

    @exception_handler("agent.registry.get")
    def get(
        self,
        identifier: str,
    ) -> AgentSpec:
        """
        Find an agent by ID or agent name.
        """

        for path in self.directory.glob("*.yaml"):

            spec = load_yaml_model(
                path,
                AgentSpec,
                f"Agent definition '{path.stem}'",
            )

            if (
                spec.id.lower()
                == identifier.lower()
                or
                spec.agent.name.lower()
                == identifier.lower()
            ):
                return spec

        raise ArtifactNotFoundError(
            artifact_name=identifier,
            artifact_type="Agent",
        )

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    @exception_handler("agent.registry.list")
    def list_agents(
        self,
    ) -> list[AgentSpec]:
        """
        Return all valid agent specifications.

        Invalid individual agent definitions are skipped so that
        one malformed definition does not prevent other agents
        from being listed.
        """

        agents: list[AgentSpec] = []

        for path in self.directory.glob("*.yaml"):

            try:
                spec = load_yaml_model(
                    path,
                    AgentSpec,
                    f"Agent definition '{path.stem}'",
                )

                agents.append(
                    spec
                )

            except ValidationError:
                # Skip invalid agent definitions.
                # The registry remains usable for valid agents.
                continue

        return agents

    @exception_handler("agent.registry.search")
    def search_agents(
        self,
        practice_area: str | None = None,
        good_at: str | None = None,
        keyword: str | None = None,
    ) -> list[AgentSpec]:
        """Search agents using practice area, good at, or keyword."""

        agents = self.list_agents()

        results = []

        for agent in agents:

            if (
                practice_area
                and agent.agent.practice_area.lower()
                != practice_area.lower()
            ):
                continue

            if (
                good_at
                and good_at.lower()
                not in [
                    item.lower()
                    for item in agent.agent.good_at
                ]
            ):
                continue

            if keyword:

                keyword_lower = keyword.lower()

                searchable_text = " ".join(
                    [
                        agent.id,
                        agent.agent.name,
                        agent.agent.details,
                        agent.agent.practice_area,
                        " ".join(agent.agent.good_at),
                    ]
                ).lower()

                if keyword_lower not in searchable_text:
                    continue

            results.append(agent)

        return results

    # ---------------------------------------------------------
    # PATH
    # ---------------------------------------------------------

    @exception_handler("agent.registry.path")
    def path_for(
        self,
        identifier: str,
    ) -> Path:
        """
        Return the YAML path for an agent.
        """

        spec = self.get(
            identifier
        )

        return (
            self.directory
            / f"{spec.id}.yaml"
        )

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    @exception_handler("agent.registry.delete")
    def delete(
        self,
        identifier: str,
    ) -> Path:
        """
        Delete an agent definition.
        """

        path = self.path_for(
            identifier
        )

        path.unlink()

        return path