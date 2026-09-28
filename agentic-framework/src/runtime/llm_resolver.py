"""Builds the crewai.LLM used for execution, based on LLM_PROVIDER env config.

This is separate from LLMGateway: LLMGateway drives agent/tool *generation*
prompts (JSON spec + Python code), while this builds the actual LLM object
CrewAI uses to *run* an agent's task.
"""
import os


def resolve_crewai_llm():
    """Execute the resolve crewai llm operation."""
    from crewai import LLM

    provider = (
    os.getenv("EXECUTION_LLM_PROVIDER")
    or os.getenv("LLM_PROVIDER")
    or "mock").lower()

    if provider == "openai":
        return LLM(model=os.getenv("OPENAI_MODEL", "gpt-4o"))

    if provider == "anthropic":
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        return LLM(model=f"anthropic/{model}")

    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        return LLM(model=f"ollama/{model}", base_url=host)

    if provider == "groq":
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        return LLM(model=f"groq/{model}")

    if provider == "gemini":
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        return LLM(model=f"gemini/{model}")

    if provider == "mock":
        raise ValueError(
            "LLM_PROVIDER=mock has no real execution backend. "
            "Set LLM_PROVIDER to openai, anthropic, or ollama in .env before running an agent or workflow."
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'")