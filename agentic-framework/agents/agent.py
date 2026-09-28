"""Module containing agent functionality for the Enterprise Agent Framework."""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class AgentMetadata(BaseModel):
    """AgentMetadata framework model or service class."""

    model_config = ConfigDict(extra="forbid")

    name: str
    details: str
    practice_area: str
    good_at: str | list[str]


class AgentBehaviour(BaseModel):
    """AgentBehaviour framework model or service class."""

    model_config = ConfigDict(extra="forbid")

    role: str
    goal: str
    back_story: str
    description: str
    expected_output: str


class LLMConfiguration(BaseModel):
    """LLMConfiguration framework model or service class."""

    model_config = ConfigDict(extra="forbid")

    provider: str = "gemini"

    model: str = ""

    temperature: float = Field(
        default=0.1,
        ge=0,
        le=2,
    )

    top_p: float = Field(
        default=0.9,
        gt=0,
        le=1,
    )

    max_iteration: int = Field(
        default=30,
        ge=1,
    )

    max_rpm: int = Field(
        default=60,
        ge=1,
    )

    max_execution_time: int = Field(
        default=500,
        ge=1,
    )


class FormatDefinition(BaseModel):
    """Definition of an agent input or output format."""

    model_config = ConfigDict(extra="forbid")

    description: str
    sample: dict | str


class AgentSpec(BaseModel):
    """AgentSpec framework model or service class."""

    model_config = ConfigDict(extra="forbid")

    id: str

    agent: AgentMetadata

    behaviour: AgentBehaviour

    llm_configuration: LLMConfiguration

    tools: list[str] = Field(
        default_factory=list
    )

    agent_skills: list[str] = Field(
        default_factory=list
    )

    kb: list[str] = Field(
        default_factory=list
    )

    guardrails: list[str] = Field(
        default_factory=list
    )

    # One prompt = one array
    prompt: list[list[str]] = Field(
        default_factory=list
    )

    input_file: list[str] = Field(
        default_factory=list
    )

    input_data: list[str] = Field(
        default_factory=list
    )

    output_data: list[str] = Field(
        default_factory=list
    )

    input_format: dict[str, FormatDefinition] | list[str] = Field(
        default_factory=dict
    )

    output_format: dict[str, FormatDefinition] | list[str] = Field(
        default_factory=dict
    )