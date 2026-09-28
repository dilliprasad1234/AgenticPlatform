"""Module containing tool factory functionality for the Enterprise Agent Framework."""

import yaml
from pydantic import ValidationError as PydanticValidationError

from src.exceptions import (
    ToolError,
    ValidationError,
    exception_handler,
)
from src.llm.gateway import LLMGateway

from tools.tool import ToolSpec


SYSTEM_PROMPT = """
You are an enterprise tool specification generator.
The user will describe a tool they want to create.
Your job is to convert the user's requirement into a
complete ToolSpec.

Return ONLY valid JSON.

Do not return Markdown.
Do not return explanations.
Do not add extra fields.

The JSON must contain exactly:

{
    "id": "",
    "name": "",
    "description": "",
    "purpose": "",
    "inputs": [],
    "output_description": "",
    "implementation_file": ""
}

Each input must contain exactly:

{
    "name": "",
    "type": "",
    "description": "",
    "required": true
}

Rules:

1. Generate a meaningful unique snake_case ID.
2. Generate a professional tool name.
3. Clearly describe what the tool does.
4. Define the purpose of the tool.
5. Identify all required inputs.
6. Identify optional inputs where appropriate.
7. Clearly describe the expected output.
8. Generate a valid snake_case Python filename.
9. Do not invent functionality that was not requested.
10. Return only the fields defined in the schema.
"""


IMPLEMENTATION_PROMPT = """
You are an enterprise Python tool implementation generator.

You will receive a validated ToolSpec.

Generate the complete Python implementation for the tool.

IMPORTANT OUTPUT RULES:

1. Return ONLY raw Python source code.
2. The first character of your response must be Python code.
3. Do NOT return Markdown.
4. Do NOT use ```python.
5. Do NOT use ``` anywhere.
6. Do NOT include headings.
7. Do NOT include explanations.
8. Do NOT include usage examples.
9. Do NOT include text before or after the Python code.

FRAMEWORK TOOL CONTRACT:

1. Import BaseTool exactly as:

from tools.base import BaseTool

2. Create exactly ONE main tool class.

3. The class name must be derived from the ToolSpec name
   using PascalCase.

4. The class MUST inherit from BaseTool.

5. The class MUST implement an execute() method.

6. The execute() method must perform the functionality
   described by the ToolSpec.

7. ALL inputs defined in ToolSpec.inputs MUST be parameters
   of the execute() method.

8. Do NOT put ToolSpec inputs in the tool class __init__() method.

9. Do NOT require constructor arguments.

10. The tool class MUST be instantiable using:

tool_class()

11. Therefore, if __init__() is implemented, it MUST NOT
    require any arguments other than self.

12. Required ToolSpec inputs MUST be validated inside
    execute().

13. Optional ToolSpec inputs MUST have appropriate
    default values in execute().

14. Use Python 3.11 type hints.

15. Add a clear class docstring.

16. Add a clear execute() method docstring.

17. The execute() method signature MUST correspond to the
    inputs defined in the ToolSpec.

18. Do not add unrelated parameters to execute().

19. Do not remove required parameters from execute().

20. The ToolSpec is the source of truth.

INPUT HANDLING:

21. Required inputs must be checked for valid values.

22. Optional inputs must be handled safely.

23. Do not request ToolSpec inputs through __init__().

24. Do not store ToolSpec input values as constructor state.

AUTHENTICATION AND SECRETS:

25. Never hardcode:
    - API keys
    - passwords
    - access tokens
    - secrets
    - credentials

26. When external authentication is required, read credentials
    from environment variables.

27. Environment variables may be used for credentials even when
    the credential itself is not listed as a ToolSpec input.

28. Never invent credentials.

29. Never print credentials, API keys, passwords, or tokens.

EXTERNAL APIs:

30. Use the API functionality described by the ToolSpec.

31. Do not invent an API endpoint when the ToolSpec does not
    provide enough information to determine one.

32. Use reasonable request timeouts.

33. Handle HTTP and network errors gracefully.

34. Parse API responses safely.

OUTPUT:

35. The returned value from execute() MUST match the
    ToolSpec.output_description as closely as possible.

36. If the ToolSpec describes a structured Python result,
    return that structured result.

37. Do not claim to create a file unless the implementation
    actually creates that file.

38. Do not return CSV, JSON files, or other files unless the
    ToolSpec explicitly requires file creation.

39. Do not invent output fields that are unrelated to the
    ToolSpec.

CODE QUALITY:

40. Keep the implementation readable and modular.

41. Use helper methods when they improve readability.

42. Use clear Python naming conventions.

43. Use type hints throughout the implementation.

44. Handle expected errors gracefully.

45. The generated code must be executable Python.

46. The generated code must be directly saveable as a .py file.

47. The generated code must be compatible with Python 3.11.

48. The generated code must be compatible with the framework's
    ToolRegistry.

49. The generated tool must be discoverable by ToolRegistry.

50. The generated tool must be instantiable without constructor
    arguments.

FINAL VALIDATION BEFORE RESPONDING:

Before returning the code, internally verify:

- Exactly one BaseTool subclass exists.
- The class inherits from BaseTool.
- The class can be instantiated as ClassName().
- No required constructor arguments exist.
- execute() contains all required ToolSpec inputs.
- Optional ToolSpec inputs have defaults.
- Required inputs are validated.
- Credentials are not hardcoded.
- External credentials use environment variables.
- The implementation matches the ToolSpec functionality.
- The returned output matches the ToolSpec.
- The result is raw executable Python only.

Return ONLY the Python source code.
"""


class ToolFactory:
    """Factory responsible for generating tool specifications and implementations."""

    def __init__(
        self,
        llm: LLMGateway,
    ):
        """Initialize the tool factory."""

        self.llm = llm

    # ---------------------------------------------------------
    # YAML SERIALIZATION
    # ---------------------------------------------------------

    @staticmethod
    def to_yaml(
        tool_spec: ToolSpec,
    ) -> str:
        """Convert a ToolSpec into YAML."""

        return yaml.safe_dump(
            tool_spec.model_dump(),
            sort_keys=False,
            allow_unicode=True,
        )

    # ---------------------------------------------------------
    # TOOL SPECIFICATION GENERATION
    # ---------------------------------------------------------

    @exception_handler("tool.factory.generate")
    def generate(
        self,
        user_requirement: str,
    ) -> ToolSpec:
        """
        Generate and validate a ToolSpec from a user requirement.
        """

        if not user_requirement.strip():
            raise ValidationError(
                "Tool requirement cannot be empty.",
                user_message=(
                    "Tool requirement cannot be empty."
                ),
            )

        raw_response = self.llm.generate_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_requirement,
        )

        try:
            tool_spec = ToolSpec.model_validate(
                raw_response
            )

        except PydanticValidationError as exc:
            raise ValidationError(
                "Generated ToolSpec failed validation.",
                user_message=(
                    "The generated tool configuration "
                    "is invalid."
                ),
            ) from exc

        return tool_spec

    # ---------------------------------------------------------
    # TOOL IMPLEMENTATION GENERATION
    # ---------------------------------------------------------

    @exception_handler("tool.factory.generate_implementation")
    def generate_implementation(
        self,
        tool_spec: ToolSpec,
    ) -> str:
        """
        Generate a Python implementation from a validated ToolSpec.
        """

        tool_spec_json = tool_spec.model_dump_json(
            indent=2
        )

        python_code = self.llm.generate(
            system_prompt=IMPLEMENTATION_PROMPT,
            user_prompt=tool_spec_json,
        )

        if not python_code.strip():
            raise ToolError(
                "LLM returned an empty tool implementation.",
                user_message=(
                    "The generated tool implementation "
                    "is empty."
                ),
            )

        return python_code