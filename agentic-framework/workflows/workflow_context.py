"""Module containing workflow context functionality for the Enterprise Agent Framework."""

from typing import Any


class WorkflowContext:

    """WorkflowContext framework model or service class."""
    def __init__(
        self,
        user_input: str,
    ):

        """Initialize the object with the supplied configuration."""
        self.user_input = user_input

        self.outputs: dict[str, Any] = {}

        self.variables: dict[str, Any] = {}

        self.current_step: str | None = None

        self.iteration = 0

    def set_output(
        self,
        step_id: str,
        output: Any,
    ) -> None:

        """Execute the set output operation."""
        self.outputs[step_id] = output

        # -----------------------------------------
        # Expose structured output as variables
        # -----------------------------------------

        if isinstance(output, dict):

            for key, value in output.items():

                self.variables[key] = value

    def get_output(
        self,
        step_id: str,
    ) -> Any:

        """Execute the get output operation."""
        return self.outputs.get(
            step_id
        )

    def latest_output(self) -> Any:

        """Execute the latest output operation."""
        if not self.outputs:
            return None

        return list(
            self.outputs.values()
        )[-1]

    def set_variable(
        self,
        name: str,
        value: Any,
    ) -> None:

        """Execute the set variable operation."""
        self.variables[name] = value

    def get_variable(
        self,
        name: str,
    ) -> Any:

        """Execute the get variable operation."""
        return self.variables.get(
            name
        )