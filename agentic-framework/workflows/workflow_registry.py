"""Module containing workflow registry functionality for the Enterprise Agent Framework."""

from contextlib import suppress
from pathlib import Path

import yaml

from src.exceptions import (
    ArtifactNotFoundError,
    ValidationError,
    exception_handler,
)
from src.utils.yaml_loader import load_yaml_model
from workflows.workflow import WorkflowSpec


class WorkflowRegistry:

    """WorkflowRegistry framework model or service class."""

    def __init__(
        self,
        directory: Path,
    ):
        """Initialize the object with the supplied configuration."""
        self.directory = directory

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    @exception_handler("workflow.registry.save")
    def save(
        self,
        spec: WorkflowSpec,
    ):
        """Execute the save operation."""

        path = (
            self.directory
            / f"{spec.id}.yaml"
        )

        path.write_text(
            yaml.safe_dump(
                spec.model_dump(
                    exclude_none=True
                ),
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

        return path

    @exception_handler("workflow.registry.get")
    def get(
        self,
        identifier: str,
    ):
        """Execute the get operation."""

        for path in self.directory.glob("*.yaml"):

            spec = self._load_workflow(
                path
            )

            if (
                spec.id.lower()
                == identifier.lower()
                or
                spec.name.lower()
                == identifier.lower()
            ):
                return spec

        raise ArtifactNotFoundError(
            artifact_name=identifier,
            artifact_type="Workflow",
        )

    @exception_handler("workflow.registry.list")
    def list_workflows(self):
        """Execute the list workflows operation."""

        workflows = []

        for path in self.directory.glob("*.yaml"):
            with suppress(ValidationError):
                spec = self._load_workflow(path)
                workflows.append(spec)

        return workflows

    @exception_handler("workflow.registry.search")
    def search_workflows(
        self,
        practice_area: str | None = None,
        good_at: str | None = None,
        keyword: str | None = None,
    ):
        """Search workflows using practice area, good at, or keyword."""

        workflows = self.list_workflows()

        results = []

        for workflow in workflows:

            # -----------------------------------------
            # Practice Area Filter
            # -----------------------------------------

            if (
                practice_area
                and workflow.practice_area.lower()
                != practice_area.lower()
            ):
                continue

            # -----------------------------------------
            # Good At Filter
            # -----------------------------------------

            if good_at:

                workflow_good_at = {
                    item.lower()
                    for item in workflow.good_at
                }

                selected_good_at = {
                    item.lower()
                    for item in good_at
                }

                if not selected_good_at.issubset(
                    workflow_good_at
                ):
                    continue

            # -----------------------------------------
            # Keyword Filter
            # -----------------------------------------

            if keyword:

                keyword_lower = keyword.lower()

                searchable_text = " ".join(
                    [
                        workflow.id,
                        workflow.name,
                        workflow.description,
                        workflow.practice_area,
                        *workflow.good_at,
                    ]
                ).lower()

                if keyword_lower not in searchable_text:
                    continue

            results.append(workflow)

        return results

    @exception_handler("workflow.registry.path")
    def path_for(
        self,
        identifier: str,
    ):
        """Execute the path for operation."""

        return (
            self.directory
            / f"{self.get(identifier).id}.yaml"
        )

    @exception_handler("workflow.registry.delete")
    def delete(
        self,
        identifier: str,
    ):
        """Execute the delete operation."""

        path = self.path_for(
            identifier
        )

        path.unlink()

        return path

    @staticmethod
    def _load_workflow(
        path: Path,
    ) -> WorkflowSpec:
        """Load and validate a workflow specification."""

        return load_yaml_model(
            path,
            WorkflowSpec,
            f"Workflow definition '{path.name}'",
        )