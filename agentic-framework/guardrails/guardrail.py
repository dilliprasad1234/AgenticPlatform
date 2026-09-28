"""Module containing guardrail functionality for the Enterprise Agent Framework."""

from pydantic import BaseModel, Field


class GuardrailSpec(BaseModel):
    """
    Defines the metadata and contract of a framework guardrail.
    """

    id: str = Field(
        min_length=1
    )

    name: str = Field(
        min_length=1
    )

    description: str = Field(
        min_length=1
    )

    type: str = Field(
        min_length=1
    )

    action: str = Field(
        default="block",
        min_length=1
    )

    implementation_file: str = Field(
        min_length=1
    )

    configuration: dict = Field(
        default_factory=dict
    )

    enabled: bool = True