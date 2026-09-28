"""Module containing workflow functionality for the Enterprise Agent Framework."""

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class WorkflowStep(BaseModel):

    """WorkflowStep framework model or service class."""
    model_config = ConfigDict(
        extra="forbid"
    )

    id: str

    type: Literal[
        "agent",
        "condition",
        "loop",
    ]

    agent: str | None = None

    condition: str | None = None

    if_true: str | None = None

    if_false: str | None = None

    next: str | None = None

    max_iterations: int | None = Field(
        default=None,
        ge=1,
    )


class WorkflowExecution(BaseModel):

    """WorkflowExecution framework model or service class."""
    model_config = ConfigDict(
        extra="forbid"
    )

    type: Literal[
        "sequential",
        "graph",
    ] = "sequential"

    steps: list[WorkflowStep] = Field(
        default_factory=list
    )


class WorkflowSpec(BaseModel):

    """WorkflowSpec framework model or service class."""
    model_config = ConfigDict(
        extra="forbid"
    )

    id: str
    name: str
    description: str
    practice_area: str
    good_at: str | list[str] = ""


    agents: list[str] = Field(
        min_length=1
    )

    execution: WorkflowExecution | None = None