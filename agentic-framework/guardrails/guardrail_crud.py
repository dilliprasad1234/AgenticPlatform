"""Module containing guardrail CRUD functionality for the Enterprise Agent Framework."""

from __future__ import annotations

from pathlib import Path

import yaml

from guardrails.guardrail import GuardrailSpec

from src.exceptions import (
    ArtifactNotFoundError,
    ValidationError,
    exception_handler,
)
from src.utils.yaml_loader import load_yaml_model


class GuardrailCRUD:
    """
    Create, read, update, and delete guardrail YAML definitions.
    """

    def __init__(self, definitions_dir: Path | None = None):
        """Initialize the object with the supplied configuration."""

        self.definitions_dir = (
            definitions_dir
            or Path(__file__).parent / "definitions"
        )

        self.definitions_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    @exception_handler("guardrail.crud.create")
    def create(
        self,
        spec: GuardrailSpec,
    ) -> Path:
        """
        Create a new guardrail definition.
        """

        file_path = (
            self.definitions_dir
            / f"{spec.id}.yaml"
        )

        if file_path.exists():
            raise ValidationError(
                f"Guardrail '{spec.id}' already exists.",
                user_message=(
                    f"Guardrail '{spec.id}' already exists."
                ),
            )

        self._write(
            spec,
            file_path,
        )

        return file_path

    @exception_handler("guardrail.crud.get")
    def get(
        self,
        guardrail_id: str,
    ) -> GuardrailSpec:
        """
        Read a guardrail definition.
        """

        file_path = (
            self.definitions_dir
            / f"{guardrail_id}.yaml"
        )

        if not file_path.exists():
            raise ArtifactNotFoundError(
                f"Guardrail '{guardrail_id}' not found.",
                user_message=(
                    f"Guardrail '{guardrail_id}' not found."
                ),
            )

        return load_yaml_model(
            file_path,
            GuardrailSpec,
            f"Guardrail definition '{guardrail_id}'",
        )

    @exception_handler("guardrail.crud.update")
    def update(
        self,
        spec: GuardrailSpec,
    ) -> Path:
        """
        Update an existing guardrail definition.
        """

        file_path = (
            self.definitions_dir
            / f"{spec.id}.yaml"
        )

        if not file_path.exists():
            raise ArtifactNotFoundError(
                f"Guardrail '{spec.id}' not found.",
                user_message=(
                    f"Guardrail '{spec.id}' not found."
                ),
            )

        self._write(
            spec,
            file_path,
        )

        return file_path

    @exception_handler("guardrail.crud.delete")
    def delete(
        self,
        guardrail_id: str,
    ) -> None:
        """
        Delete a guardrail definition.
        """

        file_path = (
            self.definitions_dir
            / f"{guardrail_id}.yaml"
        )

        if not file_path.exists():
            raise ArtifactNotFoundError(
                f"Guardrail '{guardrail_id}' not found.",
                user_message=(
                    f"Guardrail '{guardrail_id}' not found."
                ),
            )

        file_path.unlink()

    @exception_handler("guardrail.crud.list")
    def list(self) -> list[str]:
        """
        List all guardrail definition IDs.
        """

        return sorted(
            file.stem
            for file in self.definitions_dir.glob("*.yaml")
        )

    @staticmethod
    def _write(
        spec: GuardrailSpec,
        file_path: Path,
    ) -> None:
        """
        Write a GuardrailSpec to YAML.
        """

        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as f:

            yaml.safe_dump(
                spec.model_dump(),
                f,
                sort_keys=False,
                allow_unicode=True,
            )