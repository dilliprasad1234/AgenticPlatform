"""Module containing guardrail commands functionality for the Enterprise Agent Framework."""

from __future__ import annotations

from guardrails.guardrail_crud import GuardrailCRUD
from guardrails.guardrail_factory import GuardrailFactory
from src.exceptions import exception_handler


class GuardrailCommands:
    """
    High-level commands for managing guardrails.
    """

    def __init__(self):
        """Initialize the object with the supplied configuration."""
        self.crud = GuardrailCRUD()

    @exception_handler("guardrail.command.create")
    def create(
        self,
        guardrail_id: str,
        name: str,
        description: str,
        guardrail_type: str,
        implementation_file: str,
        action: str = "block",
        configuration: dict | None = None,
        enabled: bool = True,
    ):
        """
        Create a guardrail definition.
        """

        spec = GuardrailFactory.create(
            guardrail_id=guardrail_id,
            name=name,
            description=description,
            guardrail_type=guardrail_type,
            implementation_file=implementation_file,
            action=action,
            configuration=configuration,
            enabled=enabled,
        )

        return self.crud.create(spec)

    @exception_handler("guardrail.command.get")
    def get(self, guardrail_id: str):
        """
        Get a guardrail definition.
        """

        return self.crud.get(guardrail_id)

    @exception_handler("guardrail.command.update")
    def update(
        self,
        guardrail_id: str,
        name: str,
        description: str,
        guardrail_type: str,
        implementation_file: str,
        action: str = "block",
        configuration: dict | None = None,
        enabled: bool = True,
    ):
        """
        Update a guardrail definition.
        """

        spec = GuardrailFactory.create(
            guardrail_id=guardrail_id,
            name=name,
            description=description,
            guardrail_type=guardrail_type,
            implementation_file=implementation_file,
            action=action,
            configuration=configuration,
            enabled=enabled,
        )

        return self.crud.update(spec)

    @exception_handler("guardrail.command.delete")
    def delete(self, guardrail_id: str):
        """
        Delete a guardrail definition.
        """

        return self.crud.delete(guardrail_id)

    @exception_handler("guardrail.command.list")
    def list(self):
        """
        List guardrail definitions.
        """

        return self.crud.list()