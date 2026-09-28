"""LLM configuration functionality for the Enterprise Agent Framework."""

from __future__ import annotations

import os

import typer
from src.cli.prompts import prompt

from src.exceptions import (
    ConfigurationError,
    ValidationError,
    exception_handler,
)


LLM_PROVIDERS = [
    "gemini",
    "ollama",
    "openai",
    "anthropic",
]


LLM_MODEL_ENV_VARS = {
    "gemini": "GEMINI_MODEL",
    "ollama": "OLLAMA_MODEL",
    "openai": "OPENAI_MODEL",
    "anthropic": "ANTHROPIC_MODEL",
}


@exception_handler("llm.configuration.select_provider")
def select_llm_provider() -> str:
    """Prompt the user to select an LLM provider."""

    typer.echo("\nLLM Configuration\n")
    typer.echo("Available LLM Providers:\n")

    for index, provider in enumerate(
        LLM_PROVIDERS,
        start=1,
    ):
        typer.echo(
            f"{index}. {provider.capitalize()}"
        )

    choice = prompt(
        "Select LLM provider",
        type=int,
    )

    if choice < 1 or choice > len(LLM_PROVIDERS):
        raise ValidationError(
            "Invalid LLM provider selection.",
            user_message="Invalid LLM provider selection.",
        )

    return LLM_PROVIDERS[choice - 1]


@exception_handler("llm.configuration.get_model")
def get_model_for_provider(
    provider: str,
) -> str:
    """Return the configured model for the selected provider."""

    provider = provider.strip().lower()

    env_variable = LLM_MODEL_ENV_VARS.get(
        provider
    )

    if not env_variable:
        raise ConfigurationError(
            f"Unsupported LLM provider: {provider}",
            user_message=(
                f"Unsupported LLM provider: {provider}"
            ),
        )

    model = os.getenv(
        env_variable
    )

    if not model:
        raise ConfigurationError(
            f"{env_variable} is not configured in .env",
            user_message=(
                f"{env_variable} is not configured in .env"
            ),
        )

    return model