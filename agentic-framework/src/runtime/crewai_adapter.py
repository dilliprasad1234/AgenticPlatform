"""Module containing crewai adapter functionality for the Enterprise Agent Framework."""

class CrewAIRuntimeAdapter:

    """CrewAIRuntimeAdapter framework model or service class."""
    def __init__(self):
        """Initialize the object with the supplied configuration."""
        try:
            from crewai import Agent
        except ImportError as exc:
            raise RuntimeError(
                "Install CrewAI with: pip install -e '.[crewai]'"
            ) from exc

        self.Agent = Agent

    def build_agent(self, spec, tools=None, llm=None):

        """Execute the build agent operation."""
        kwargs = {
            "role": spec.behaviour.role,
            "goal": spec.behaviour.goal,
            "backstory": spec.behaviour.back_story,
            "tools": tools or [],
            "verbose": True,
            "max_iter": spec.llm_configuration.max_iteration,
            "max_rpm": spec.llm_configuration.max_rpm,
            "max_execution_time": spec.llm_configuration.max_execution_time,
        }

        if llm is not None:
            kwargs["llm"] = llm

        return self.Agent(**kwargs)