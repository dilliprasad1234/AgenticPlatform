"""Module containing agent factory functionality for the Enterprise Agent Framework."""

import yaml
from pydantic import ValidationError as PydanticValidationError

from agents.agent import AgentSpec

from src.exceptions import (
    ValidationError,
    exception_handler,
)

from src.llm.gateway import LLMGateway


SYSTEM_PROMPT = """
You are an enterprise agent specification generator.

The user will describe what they want an AI agent to do.

Your job is to convert the user's requirement into a
complete AgentSpec.

Return ONLY valid JSON.

Do not return Markdown.
Do not return explanations.
Do not add extra fields.

The JSON must contain exactly:

{
    "id": "",
    "agent": {
        "name": "",
        "details": "",
        "practice_area": "",
        "good_at": ""
    },
    "behaviour": {
        "role": "",
        "goal": "",
        "back_story": "",
        "description": "",
        "expected_output": ""
    },
    "llm_configuration": {
        "model": "gemini",
        "temperature": 0.1,
        "top_p": 0.9,
        "max_iteration": 30,
        "max_rpm": 60,
        "max_execution_time": 500
    },
    "tools": [],
    "agent_skills": [],
    "kb": [],
    "guardrails": [],
    "prompt": [],
    "input_format": [],
    "output_format": []
}

Rules:

1. Generate a meaningful unique snake_case ID.
2. Infer the practice area from the requirement.
3. Identify the agent's core competencies.
4. Create a professional role.
5. Define a clear goal.
6. Define a useful back story.
7. Provide a detailed description with steps in a clear way.
8. Define the expected output.
9. Do not invent tools unless explicitly requested.
10. tools should initially be [].
11. Populate agent_skills with the skills required by the agent.
12. kb should initially be [].
13. Populate prompt as a list of arrays.
    Each prompt must be represented as its own array containing
    one or more prompt instruction strings.

    Correct:
    "prompt": [
        ["Fetch user stories from Jira."],
        ["Validate that each story contains an ID and summary."]
    ]

    Incorrect:
    "prompt": [
        "Fetch user stories from Jira.",
        "Validate that each story contains an ID and summary."
    ]
14. Populate input_file with the types of files the agent expects as input.
15. Populate input_data with the expected input fields and their meaning.
16. Populate output_data with the expected output fields and their meaning.
17. Populate input_format based on the actual input expected by the agent.

    input_format must be an object where each supported format
    contains:
    - description: a short explanation of the expected input.
    - sample: a realistic example that the user can directly enter.

    The sample must represent the actual input structure of the agent.
    Do not wrap the sample inside generic fields such as "user_input"
    unless the agent specifically requires that field.

    Example for a weather agent:

    "input_format": {
        "json": {
            "description": "JSON object containing the target country or city.",
            "sample": {
                "City": "Chennai"
            }
        }
    }

18. Populate output_format based on the actual output produced by the agent.

    output_format must be an object where each supported format
    contains:
    - description: a short explanation of the expected output.
    - sample: a realistic example of the expected output.

19. Only include input formats that the agent actually supports.
20. The sample input must be directly usable by the user during agent execution.
21. Do not invent input fields that are not relevant to the agent requirement.
22. If runtime input is optional for the agent, the input format should still
    describe the expected input when input is provided.s
"""


class AgentFactory:
    """Factory responsible for generating agent specifications."""

    def __init__(
        self,
        llm: LLMGateway,
    ):
        """Initialize the agent factory."""

        self.llm = llm

    # ---------------------------------------------------------
    # AGENT SPECIFICATION GENERATION
    # ---------------------------------------------------------

    @exception_handler("agent.factory.generate")
    def generate(
        self,
        user_requirement: str,
    ) -> AgentSpec:
        """
        Generate and validate an AgentSpec from a user requirement.
        """

        if not user_requirement.strip():
            raise ValidationError(
                "Agent requirement cannot be empty.",
                user_message=(
                    "Agent requirement cannot be empty."
                ),
            )

        raw_response = self.llm.generate_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_requirement,
        )

        try:
            agent_spec = AgentSpec.model_validate(
                raw_response
            )

        except PydanticValidationError as exc:
            raise ValidationError(
                "Generated AgentSpec failed validation.",
                user_message=(
                    "The generated agent configuration "
                    "is invalid."
                ),
            ) from exc

        return agent_spec

    # ---------------------------------------------------------
    # YAML SERIALIZATION
    # ---------------------------------------------------------

    @staticmethod
    def to_yaml(
        agent_spec: AgentSpec,
    ) -> str:
        """
        Convert an AgentSpec into YAML.
        """

        return yaml.safe_dump(
            agent_spec.model_dump(),
            sort_keys=False,
            allow_unicode=True,
        )