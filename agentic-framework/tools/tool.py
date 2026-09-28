"""Module containing tool functionality for the Enterprise Agent Framework."""

from pydantic import BaseModel, Field

class ToolInput(BaseModel):
    """
    Defines an input parameter accepted by a tool.
    """

    name: str = Field(
        min_length=1
    )

    type: str = Field(
        min_length=1
    )

    description: str = Field(
        min_length=1
    )

    required: bool = True


class ToolSpec(BaseModel):
    """
    Defines the metadata and contract of a framework tool.
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

    purpose: str = Field(
        min_length=1
    )

    inputs: list[ToolInput] = Field(
        default_factory=list
    )

    output_description: str = Field(
        min_length=1
    )

    implementation_file: str = Field(
        min_length=1
    )