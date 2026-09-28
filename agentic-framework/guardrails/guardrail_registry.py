"""Module containing guardrail registry functionality for the Enterprise Agent Framework."""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from contextlib import suppress
from guardrails.base import BaseGuardrail
from guardrails.guardrail import GuardrailSpec

from src.exceptions import (
    ArtifactNotFoundError,
    ValidationError,
    exception_handler,
)
from src.utils.yaml_loader import load_yaml_model


class GuardrailRegistry:
    """
    Discovers and manages guardrail implementations
    and their YAML definitions.
    """

    def __init__(self):
        """Initialize the object with the supplied configuration."""
        self._guardrails: dict[str, type[BaseGuardrail]] = {}
        self._specs: dict[str, GuardrailSpec] = {}

        self._discover_guardrails()
        self._load_definitions()

    def _discover_guardrails(self) -> None:
        """
        Discover all BaseGuardrail implementations
        from the guardrails/implementations directory.
        """

        implementations_dir = (
            Path(__file__).parent / "implementations"
        )

        if not implementations_dir.exists():
            return

        for file in implementations_dir.glob("*.py"):

            if file.name.startswith("_"):
                continue

            module_name = (
                f"guardrails.implementations.{file.stem}"
            )

            module = importlib.import_module(
                module_name
            )

            for name, obj in inspect.getmembers(
                module,
                inspect.isclass,
            ):

                if (
                    issubclass(obj, BaseGuardrail)
                    and obj is not BaseGuardrail
                ):
                    self._guardrails[name] = obj

    def _load_definitions(self) -> None:
        """
        Load all guardrail YAML definitions.
        """

        definitions_dir = (
            Path(__file__).parent / "definitions"
        )

        if not definitions_dir.exists():
            return

        for file in definitions_dir.glob("*.yaml"):
            with suppress(ValidationError):
                spec = load_yaml_model(file, GuardrailSpec, f"Guardrail definition '{file.name}'",)
                self._specs[spec.id] = spec

    @exception_handler("guardrail.registry.register")
    def register(
        self,
        name: str,
        guardrail_class: type[BaseGuardrail],
    ) -> None:
        """
        Register a guardrail implementation.
        """

        if not issubclass(
            guardrail_class,
            BaseGuardrail,
        ):
            raise ValidationError(
                "Guardrail must inherit from BaseGuardrail.",
                user_message=(
                    "Invalid guardrail implementation."
                ),
            )

        self._guardrails[name] = guardrail_class

    @exception_handler("guardrail.registry.get")
    def get(
        self,
        name: str,
    ) -> type[BaseGuardrail]:
        """
        Get a guardrail implementation by class name.
        """

        if name not in self._guardrails:
            raise ArtifactNotFoundError(
                f"Guardrail '{name}' not found.",
                user_message=(
                    f"Guardrail '{name}' not found."
                ),
            )

        return self._guardrails[name]

    @exception_handler("guardrail.registry.get_spec")
    def get_spec(
        self,
        guardrail_id: str,
    ) -> GuardrailSpec:
        """
        Get a guardrail specification by ID.
        """

        if guardrail_id not in self._specs:
            raise ArtifactNotFoundError(
                f"Guardrail definition "
                f"'{guardrail_id}' not found.",
                user_message=(
                    f"Guardrail '{guardrail_id}' not found."
                ),
            )

        return self._specs[guardrail_id]

    @exception_handler("guardrail.registry.get_by_id")
    def get_by_id(
        self,
        guardrail_id: str,
    ) -> type[BaseGuardrail]:
        """
        Resolve a guardrail definition ID
        to its implementation class.
        """

        spec = self.get_spec(
            guardrail_id
        )

        implementation_name = Path(
            spec.implementation_file
        ).stem

        # Convert:
        #
        # block_violent_harmful_input
        #
        # into:
        #
        # BlockViolentHarmfulInputGuardrail
        #

        expected_class_name = (
            "".join(
                part.capitalize()
                for part in implementation_name.split("_")
            )
            + "Guardrail"
        )

        for (
            name,
            guardrail_class,
        ) in self._guardrails.items():

            if name == expected_class_name:
                return guardrail_class

        raise ArtifactNotFoundError(
            f"No implementation found for guardrail "
            f"'{guardrail_id}'. "
            f"Expected implementation class "
            f"'{expected_class_name}'.",
            user_message=(
                f"No implementation found for guardrail "
                f"'{guardrail_id}'."
            ),
        )

    @exception_handler("guardrail.registry.list")
    def list_guardrails(self) -> list[str]:
        """
        List discovered guardrail implementation classes.
        """

        return sorted(
            self._guardrails.keys()
        )

    @exception_handler("guardrail.registry.list_specs")
    def list_specs(self) -> list[str]:
        """
        List guardrail definition IDs.
        """

        return sorted(
            self._specs.keys()
        )