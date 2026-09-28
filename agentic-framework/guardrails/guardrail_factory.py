"""Module containing guardrail factory functionality for the Enterprise Agent Framework."""

from __future__ import annotations

import ast
import importlib.util
import tempfile
from pathlib import Path

import yaml

from guardrails.guardrail import GuardrailSpec

from src.exceptions import (
    GuardrailError,
    LLMError,
    ValidationError,
    exception_handler,
)
from src.llm.gateway import LLMGateway


SPEC_SYSTEM_PROMPT = """
You are an enterprise guardrail specification generator.

The user will describe a guardrail they want to create.
Convert the requirement into a complete GuardrailSpec.

Return ONLY valid JSON.
Do not return Markdown.
Do not return explanations.
Do not add extra fields.

The JSON must contain exactly:

{
    "id": "",
    "name": "",
    "description": "",
    "type": "",
    "action": "block",
    "implementation_file": "",
    "configuration": {},
    "enabled": true
}

Rules:

1. Generate a meaningful unique snake_case ID.
2. Generate a professional guardrail name.
3. Clearly describe what the guardrail validates.
4. The type should describe where the guardrail applies,
   such as input, output, or content.
5. The action should normally be "block".
6. Generate a valid snake_case Python filename ending in .py.
7. Put configurable values inside configuration.
8. Do not invent functionality that was not requested.
9. Return only the fields defined in the schema.
"""


IMPLEMENTATION_PROMPT = """
You are an enterprise Python guardrail implementation generator.

You will receive a validated GuardrailSpec.

Generate the complete Python implementation for the guardrail.

IMPORTANT OUTPUT RULES:

1. Return ONLY raw Python source code.
2. Do NOT return Markdown.
3. Do NOT use ```python.
4. Do NOT include headings.
5. Do NOT include explanations.
6. Do NOT include usage examples.
7. Do NOT include text before or after the Python code.

FRAMEWORK GUARDRAIL CONTRACT:

1. Import BaseGuardrail exactly as:

from guardrails.base import BaseGuardrail

2. Create exactly ONE main guardrail class.
3. The class MUST inherit from BaseGuardrail.
4. The class MUST implement:

validate(
    self,
    value,
    context=None
)

5. The validate method MUST return:

(True, value)

when validation passes.

6. The validate method MUST return:

(False, reason)

when validation fails.

7. Configuration values from GuardrailSpec.configuration
   should be accepted by __init__ when required.

8. The guardrail must be instantiable by the framework using:

guardrail_class(**configuration)

9. Do not hardcode secrets, passwords, API keys, or tokens.
10. Do not invent external APIs.
11. Use Python 3.11 compatible code.
12. Add a clear class docstring.
13. Add a clear validate method docstring.
14. The implementation must match the GuardrailSpec exactly.
15. The generated code must be directly saveable as a .py file.
16. The generated guardrail must be discoverable by GuardrailRegistry.

VALIDATION BEHAVIOR:

The guardrail must actually perform the validation
described in the GuardrailSpec.

The implementation must handle the actual runtime value type.

For output guardrails, the value may be:

- plain text
- JSON text
- dictionaries
- lists
- serialized agent output

Do not assume output is always a dictionary.

If the requirement detects sensitive information, inspect
the actual content rather than relying on one exact format.

Do not create overly restrictive patterns that only match
one specific example.

The guardrail should detect the semantic condition described
by the requirement across reasonable formatting variations.

Return ONLY the Python source code.
"""


REPAIR_PROMPT = """
You are repairing an enterprise Python guardrail implementation.

The GuardrailSpec, generated implementation, and behavioral
test failures will be provided.

Your job is to fix the implementation so that it correctly
implements the GuardrailSpec.

IMPORTANT:

1. Return ONLY raw Python source code.
2. Do NOT return Markdown.
3. Do NOT use ```python.
4. Do NOT include explanations.
5. Keep the same GuardrailSpec.
6. Keep the BaseGuardrail contract.
7. The class must inherit from BaseGuardrail.
8. validate(self, value, context=None) must be implemented.
9. Successful validation must return (True, value).
10. Failed validation must return (False, reason).
11. Handle realistic runtime value types.
12. Do not hardcode one specific test value.
13. Fix the underlying validation logic rather than
    creating a special case for the test.
14. Do not invent external APIs.
15. The result must be executable Python.

Return ONLY the corrected Python source code.
"""


BEHAVIOR_TEST_PROMPT = """
You are an enterprise guardrail behavioral test generator.

You will receive a GuardrailSpec.

Generate behavioral test cases that verify whether the
guardrail actually implements the requirement.

Return ONLY valid JSON.

Return exactly this structure:

{
    "tests": [
        {
            "name": "",
            "value": null,
            "expected_pass": true
        }
    ]
}

Rules:

1. Generate both positive and negative tests when applicable.
2. Negative tests must contain realistic examples that
   should be rejected by the guardrail.
3. Positive tests must contain realistic safe/valid examples.
4. Do not use only trivial empty values.
5. For content detection guardrails, test realistic variations.
6. For output guardrails, include realistic serialized text
   when the runtime may provide string output.
7. Do not test anything unrelated to the GuardrailSpec.
8. Keep the number of tests between 2 and 6.
9. Return only valid JSON.
"""


class GuardrailFactory:
    """GuardrailFactory framework model or service class."""

    MAX_REPAIR_ATTEMPTS = 3

    def __init__(
        self,
        llm: LLMGateway,
    ):
        """Initialize the object with the supplied configuration."""
        self.llm = llm

    @staticmethod
    @exception_handler("guardrail.factory.to_yaml")
    def to_yaml(
        spec: GuardrailSpec,
    ) -> str:
        """Execute the to yaml operation."""

        return yaml.safe_dump(
            spec.model_dump(),
            sort_keys=False,
            allow_unicode=True,
        )

    @staticmethod
    @exception_handler("guardrail.factory.create")
    def create(
        guardrail_id: str,
        name: str,
        description: str,
        guardrail_type: str,
        implementation_file: str,
        action: str = "block",
        configuration: dict | None = None,
        enabled: bool = True,
    ) -> GuardrailSpec:
        """Create a validated GuardrailSpec without invoking an LLM."""

        return GuardrailSpec(
            id=guardrail_id,
            name=name,
            description=description,
            type=guardrail_type,
            action=action,
            implementation_file=implementation_file,
            configuration=configuration or {},
            enabled=enabled,
        )

    @exception_handler("guardrail.factory.generate")
    def generate(
        self,
        user_requirement: str,
    ) -> GuardrailSpec:
        """Execute the generate operation."""

        if not user_requirement.strip():
            raise ValidationError(
                "Guardrail requirement cannot be empty.",
                user_message=(
                    "Guardrail requirement cannot be empty."
                ),
            )

        raw_response = self.llm.generate_json(
            system_prompt=SPEC_SYSTEM_PROMPT,
            user_prompt=user_requirement,
        )

        try:
            return GuardrailSpec.model_validate(
                raw_response
            )

        except Exception as exc:
            raise ValidationError(
                "Generated guardrail specification is invalid.",
                user_message=(
                    "The generated guardrail specification is invalid."
                ),
            ) from exc

    @exception_handler("guardrail.factory.generate_implementation")
    def generate_implementation(
        self,
        guardrail_spec: GuardrailSpec,
    ) -> str:
        """Execute the generate implementation operation."""

        guardrail_spec_json = (
            guardrail_spec.model_dump_json(
                indent=2
            )
        )

        python_code = self.llm.generate(
            system_prompt=IMPLEMENTATION_PROMPT,
            user_prompt=guardrail_spec_json,
        )

        if not python_code.strip():
            raise GuardrailError(
                "LLM returned an empty guardrail implementation.",
                user_message=(
                    "The generated guardrail implementation is empty."
                ),
            )

        for attempt in range(
            1,
            self.MAX_REPAIR_ATTEMPTS + 1,
        ):

            try:
                self._validate_generated_code(
                    python_code,
                    guardrail_spec,
                )

                self._validate_behavior(
                    python_code,
                    guardrail_spec,
                )

                return python_code

            except LLMError:
                raise

            except (
                ValidationError,
                GuardrailError,
            ) as exc:

                if attempt >= self.MAX_REPAIR_ATTEMPTS:
                    raise GuardrailError(
                        "Generated guardrail failed behavioral "
                        "validation after "
                        f"{self.MAX_REPAIR_ATTEMPTS} attempts: {exc}",
                        user_message=(
                            "The generated guardrail could not be "
                            "validated after "
                            f"{self.MAX_REPAIR_ATTEMPTS} attempts."
                        ),
                    ) from exc

                repair_prompt = (
                    f"GuardrailSpec:\n"
                    f"{guardrail_spec_json}\n\n"
                    f"Generated implementation:\n"
                    f"{python_code}\n\n"
                    f"Validation failure:\n"
                    f"{exc}\n\n"
                    f"Generate the corrected implementation."
                )

                python_code = self.llm.generate(
                    system_prompt=REPAIR_PROMPT,
                    user_prompt=repair_prompt,
                )

                if not python_code.strip():
                    raise GuardrailError(
                        "LLM returned an empty repaired "
                        "guardrail implementation.",
                        user_message=(
                            "The repaired guardrail implementation "
                            "is empty."
                        ),
                    )

        raise GuardrailError(
            "Guardrail implementation generation failed.",
            user_message=(
                "Guardrail implementation generation failed."
            ),
        )

    def _validate_behavior(
        self,
        python_code: str,
        guardrail_spec: GuardrailSpec,
    ) -> None:
        """Validate generated guardrail behavior."""

        test_response = self.llm.generate_json(
            system_prompt=BEHAVIOR_TEST_PROMPT,
            user_prompt=guardrail_spec.model_dump_json(
                indent=2
            ),
        )

        tests = test_response.get("tests")

        if not isinstance(tests, list) or not tests:
            raise ValidationError(
                "LLM did not generate valid behavioral tests.",
                user_message=(
                    "The LLM did not generate valid behavioral tests."
                ),
            )

        guardrail_class = self._load_generated_class(
            python_code,
            guardrail_spec,
        )

        configuration = (
            guardrail_spec.configuration or {}
        )

        try:
            instance = guardrail_class(
                **configuration
            )

        except Exception as exc:
            raise GuardrailError(
                f"Generated guardrail could not be "
                f"instantiated: {exc}",
                user_message=(
                    "The generated guardrail could not be "
                    "instantiated."
                ),
            ) from exc

        failures: list[str] = []

        for test in tests:

            if not isinstance(test, dict):
                failures.append(
                    "Invalid behavioral test format."
                )
                continue

            if (
                "value" not in test
                or "expected_pass" not in test
            ):
                failures.append(
                    f"Invalid behavioral test: {test}"
                )
                continue

            value = test["value"]
            expected_pass = bool(
                test["expected_pass"]
            )

            try:
                result = instance.validate(
                    value,
                    context=None,
                )

            except Exception as exc:
                failures.append(
                    f"Test '{test.get('name', 'unnamed')}' "
                    f"raised exception: {exc}"
                )
                continue

            if (
                not isinstance(result, tuple)
                or len(result) != 2
                or not isinstance(result[0], bool)
            ):
                failures.append(
                    f"Test '{test.get('name', 'unnamed')}' "
                    "returned an invalid guardrail result."
                )
                continue

            actual_pass = result[0]

            if actual_pass != expected_pass:
                failures.append(
                    f"Test '{test.get('name', 'unnamed')}' failed. "
                    f"Expected pass={expected_pass}, "
                    f"actual pass={actual_pass}, "
                    f"value={value!r}, result={result!r}"
                )

            if actual_pass and result[1] != value:
                failures.append(
                    f"Test '{test.get('name', 'unnamed')}' "
                    "modified the value even though validation passed."
                )

        if failures:
            raise GuardrailError(
                "Behavioral validation failed:\n"
                + "\n".join(failures),
                user_message=(
                    "The generated guardrail failed behavioral validation."
                ),
            )

    @staticmethod
    def _load_generated_class(
        python_code: str,
        guardrail_spec: GuardrailSpec,
    ):
        """Load the generated guardrail class."""

        implementation_name = (
            guardrail_spec.implementation_file
        )

        if implementation_name.endswith(".py"):
            implementation_name = implementation_name[:-3]

        expected_class_name = (
            "".join(
                part.capitalize()
                for part in implementation_name.split("_")
            )
            + "Guardrail"
        )

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = (
                Path(temp_dir)
                / f"{implementation_name}.py"
            )

            temp_path.write_text(
                python_code,
                encoding="utf-8",
            )

            module_spec = (
                importlib.util.spec_from_file_location(
                    implementation_name,
                    temp_path,
                )
            )

            if (
                module_spec is None
                or module_spec.loader is None
            ):
                raise ValidationError(
                    "Unable to load generated guardrail module.",
                    user_message=(
                        "Unable to load the generated guardrail module."
                    ),
                )

            module = (
                importlib.util.module_from_spec(
                    module_spec
                )
            )

            try:
                module_spec.loader.exec_module(
                    module
                )

            except Exception as exc:
                raise GuardrailError(
                    f"Generated guardrail could not be imported: {exc}",
                    user_message=(
                        "The generated guardrail could not be imported."
                    ),
                ) from exc

            guardrail_class = getattr(
                module,
                expected_class_name,
                None,
            )

            if guardrail_class is None:
                raise ValidationError(
                    f"Generated guardrail class "
                    f"'{expected_class_name}' was not found.",
                    user_message=(
                        f"Generated guardrail class "
                        f"'{expected_class_name}' was not found."
                    ),
                )

            return guardrail_class

    @staticmethod
    def _validate_generated_code(
        python_code: str,
        guardrail_spec: GuardrailSpec,
    ) -> None:
        """Validate the generated Python guardrail contract."""

        try:
            tree = ast.parse(
                python_code
            )

        except SyntaxError as exc:
            raise ValidationError(
                "Generated guardrail contains invalid Python syntax.",
                user_message=(
                    "The generated guardrail contains invalid "
                    "Python syntax."
                ),
            ) from exc

        guardrail_classes = []

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.ClassDef,
            ):
                continue

            inherits_base_guardrail = any(
                (
                    isinstance(base, ast.Name)
                    and base.id == "BaseGuardrail"
                )
                or (
                    isinstance(base, ast.Attribute)
                    and base.attr == "BaseGuardrail"
                )
                for base in node.bases
            )

            if inherits_base_guardrail:
                guardrail_classes.append(node)

        if len(guardrail_classes) != 1:
            raise ValidationError(
                "Generated guardrail must contain exactly one "
                "BaseGuardrail subclass.",
                user_message=(
                    "Generated guardrail must contain exactly one "
                    "BaseGuardrail class."
                ),
            )

        guardrail_class = guardrail_classes[0]

        implementation_name = (
            guardrail_spec.implementation_file
        )

        if implementation_name.endswith(".py"):
            implementation_name = implementation_name[:-3]

        expected_class_name = (
            "".join(
                part.capitalize()
                for part in implementation_name.split("_")
            )
            + "Guardrail"
        )

        if guardrail_class.name != expected_class_name:
            raise ValidationError(
                "Generated guardrail class name is invalid. "
                f"Expected '{expected_class_name}', "
                f"but received '{guardrail_class.name}'.",
                user_message=(
                    "Generated guardrail class name is invalid."
                ),
            )

        validate_method = None

        for node in guardrail_class.body:

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ) and node.name == "validate":

                validate_method = node
                break

        if validate_method is None:
            raise ValidationError(
                "Generated guardrail must implement validate().",
                user_message=(
                    "Generated guardrail must implement validate()."
                ),
            )

        arguments = validate_method.args.args

        argument_names = [
            argument.arg
            for argument in arguments
        ]

        if len(argument_names) < 2:
            raise ValidationError(
                "Guardrail validate() must accept at least "
                "'self' and 'value'.",
                user_message=(
                    "Guardrail validate() must accept "
                    "'self' and 'value'."
                ),
            )

        if argument_names[0] != "self":
            raise ValidationError(
                "Guardrail validate() first parameter must be 'self'.",
                user_message=(
                    "Guardrail validate() first parameter must be 'self'."
                ),
            )

        if argument_names[1] != "value":
            raise ValidationError(
                "Guardrail validate() second parameter must be 'value'.",
                user_message=(
                    "Guardrail validate() second parameter must be 'value'."
                ),
            )

        if len(argument_names) >= 3:

            if argument_names[2] != "context":
                raise ValidationError(
                    "Guardrail validate() third parameter must be "
                    "'context' when provided.",
                    user_message=(
                        "Guardrail validate() third parameter must be "
                        "'context' when provided."
                    ),
                )

        init_method = None

        for node in guardrail_class.body:

            if isinstance(
                node,
                ast.FunctionDef,
            ):
                if node.name == "__init__":
                    init_method = node
                    break

        configuration = (
            guardrail_spec.configuration or {}
        )

        if configuration and init_method is None:
            raise ValidationError(
                "GuardrailSpec contains configuration values, "
                "but generated guardrail has no __init__ method.",
                user_message=(
                    "The generated guardrail does not accept "
                    "the configured values."
                ),
            )

        if init_method is not None:

            init_arguments = {
                argument.arg
                for argument in init_method.args.args
                if argument.arg != "self"
            }

            missing_configuration = [
                key
                for key in configuration
                if key not in init_arguments
            ]

            if missing_configuration:
                raise ValidationError(
                    "Generated guardrail __init__ does not accept "
                    f"configuration values: {missing_configuration}",
                    user_message=(
                        "The generated guardrail does not accept "
                        "all configured values."
                    ),
                )

        has_tuple_return = False

        for node in ast.walk(
            validate_method
        ):

            if not isinstance(
                node,
                ast.Return,
            ):
                continue

            value = node.value

            if not isinstance(
                value,
                ast.Tuple,
            ):
                continue

            if len(value.elts) != 2:
                continue

            first_element = value.elts[0]

            if (
                isinstance(
                    first_element,
                    ast.Constant,
                )
                and first_element.value in (
                    True,
                    False,
                )
            ):
                has_tuple_return = True
                break

        if not has_tuple_return:
            raise ValidationError(
                "Generated guardrail validate() must return "
                "(True, value) or (False, reason).",
                user_message=(
                    "Generated guardrail validate() must return "
                    "(True, value) or (False, reason)."
                ),
            )