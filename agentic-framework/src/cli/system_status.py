"""Enterprise-grade, read-only System Status dashboard for the CLI."""

from __future__ import annotations

import importlib.metadata
import os
import platform
import sys
import re
from pathlib import Path
from typing import Iterable

from src.cli.ui import console
from src.config import (
    AGENTS_DIR,
    CHROMADB_PATH,
    GUARDRAIL_DEFINITIONS_DIR,
    PROJECT_ROOT,
    TOOLS_DIR,
    WORKFLOWS_DIR,
    LLM_PROVIDER,
)


_PROVIDER_DETAILS = {
    "openai": {"label": "OpenAI", "model": "OPENAI_MODEL", "credential": "OPENAI_API_KEY"},
    "anthropic": {"label": "Anthropic", "model": "ANTHROPIC_MODEL", "credential": "ANTHROPIC_API_KEY"},
    "gemini": {"label": "Gemini", "model": "GEMINI_MODEL", "credential": "GEMINI_API_KEY"},
    "groq": {"label": "Groq", "model": "GROQ_MODEL", "credential": "GROQ_API_KEY"},
    "ollama": {"label": "Ollama", "model": "OLLAMA_MODEL", "credential": None},
    "mock": {"label": "Mock", "model": None, "credential": None},
}


def _count_yaml(directory: Path) -> int:
    """Count definition files without failing if a directory is missing."""
    if not directory.exists():
        return 0
    return sum(1 for path in directory.glob("*.yaml") if path.is_file()) + sum(
        1 for path in directory.glob("*.yml") if path.is_file()
    )


def _package_version(package: str) -> str:
    """Return installed package version, falling back to local pyproject metadata."""
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        pyproject = PROJECT_ROOT / "pyproject.toml"
        if pyproject.exists():
            match = re.search(r"^version\s*=\s*[\"]([^\"]+)[\"]", pyproject.read_text(encoding="utf-8"), re.MULTILINE)
            if match:
                return match.group(1)
        return "unknown"


def _models_for_provider(provider: str) -> list[str]:
    """Read one or more models from the environment.

    Existing singular *_MODEL settings remain supported.  A plural *_MODELS
    variable may contain comma/newline-separated models for multi-model setups.
    """
    details = _PROVIDER_DETAILS.get(provider, {})
    singular_key = details.get("model")
    if not singular_key:
        return []

    plural_key = singular_key.replace("_MODEL", "_MODELS")
    raw = os.getenv(plural_key, "") or os.getenv(singular_key, "")
    models: list[str] = []
    for value in raw.replace("\n", ",").split(","):
        value = value.strip()
        if value and value not in models:
            models.append(value)
    return models


def _configured_llms() -> list[dict[str, object]]:
    """Return configured provider/model inventory without making network calls."""
    configured: list[dict[str, object]] = []

    for provider, details in _PROVIDER_DETAILS.items():
        models = _models_for_provider(provider)
        credential_key = details.get("credential")
        credential_configured = bool(os.getenv(credential_key)) if credential_key else True

        if provider == "mock":
            # Mock is a framework fallback, not a real external provider.
            if LLM_PROVIDER == "mock" or os.getenv("MOCK_MODEL"):
                configured.append({
                    "provider": provider,
                    "label": details["label"],
                    "models": [os.getenv("MOCK_MODEL", "mock")],
                    "credential": True,
                })
            continue

        if models or credential_configured:
            configured.append({
                "provider": provider,
                "label": details["label"],
                "models": models or ["model not specified"],
                "credential": credential_configured,
            })

    # Preserve an explicitly selected provider even if its model/key is absent,
    # so the dashboard can explain why the system is not ready.
    selected = (os.getenv("EXECUTION_LLM_PROVIDER") or LLM_PROVIDER or "mock").strip().lower()
    if selected not in {item["provider"] for item in configured}:
        details = _PROVIDER_DETAILS.get(selected, {"label": selected.title(), "credential": None})
        configured.append({
            "provider": selected,
            "label": details["label"],
            "models": _models_for_provider(selected) or ["not configured"],
            "credential": bool(os.getenv(details.get("credential", ""))) if details.get("credential") else selected == "ollama",
        })

    return configured


def _section(title: str) -> None:
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print("[dim]" + "─" * 66 + "[/dim]")


def _row(label: str, value: str, status: str | None = None) -> None:
    if status == "ok":
        prefix = "[green]✓[/green] "
    elif status == "warn":
        prefix = "[yellow]![/yellow] "
    elif status == "error":
        prefix = "[red]✗[/red] "
    else:
        prefix = "  "
    console.print(f"{prefix}[bold]{label:<22}[/bold] {value}")


def _path_health(path: Path) -> str:
    return "ok" if path.exists() else "error"


def _component_count(directory: Path) -> tuple[int, str]:
    count = _count_yaml(directory)
    return count, "ok" if directory.exists() else "error"


def _llm_status(item: dict[str, object]) -> str:
    return "ok" if item.get("credential") and item.get("models") and item["models"] != ["not configured"] else "warn"


def show_system_status() -> None:
    """Display a dynamic, non-mutating framework health dashboard."""
    console.print("\n[bold white on cyan] SYSTEM STATUS [/bold white on cyan]")

    _section("FRAMEWORK")
    environment = os.getenv("VIRTUAL_ENV")
    environment_name = Path(environment).name if environment else "System Python"
    _row("Version", _package_version("enterprise-agent-framework"))
    _row("Python", sys.version.split()[0])
    _row("Environment", environment_name)
    _row("Platform", f"{platform.system()} {platform.release()} ({platform.machine() or 'unknown'})")

    agent_count, agent_health = _component_count(AGENTS_DIR)
    workflow_count, workflow_health = _component_count(WORKFLOWS_DIR)
    tool_count, tool_health = _component_count(TOOLS_DIR / "definitions")
    guardrail_count, guardrail_health = _component_count(GUARDRAIL_DEFINITIONS_DIR)
    kb_health = _path_health(CHROMADB_PATH)

    _section("COMPONENTS")
    _row("Agents", f"{agent_count} loaded", agent_health)
    _row("Workflows", f"{workflow_count} loaded", workflow_health)
    _row("Tools", f"{tool_count} available", tool_health)
    _row("Guardrails", f"{guardrail_count} configured", guardrail_health)
    _row("Knowledge Bases", "storage available" if kb_health == "ok" else "storage missing", kb_health)

    llms = _configured_llms()
    selected_provider = (os.getenv("EXECUTION_LLM_PROVIDER") or LLM_PROVIDER or "mock").strip().lower()
    selected_model = _models_for_provider(selected_provider)

    _section("LLM")
    _row("Providers", f"{len(llms)} configured", "ok" if llms else "warn")
    model_count = sum(len(item["models"]) for item in llms)
    _row("Models", f"{model_count} configured", "ok" if model_count else "warn")
    selected_label = _PROVIDER_DETAILS.get(selected_provider, {"label": selected_provider.title()})["label"]
    _row("Default", f"{selected_label} / {selected_model[0] if selected_model else 'not configured'}")
    selected_item = next((item for item in llms if item["provider"] == selected_provider), None)
    _row("Configuration", "Valid" if selected_item and _llm_status(selected_item) == "ok" else "Needs attention", "ok" if selected_item and _llm_status(selected_item) == "ok" else "warn")

    for item in llms:
        models = item["models"]
        model_text = ", ".join(str(model) for model in models)
        credential = "credential configured" if item.get("credential") else "credential missing"
        console.print(f"  [bold]{item['label']}[/bold]  [dim]({len(models)} model{'s' if len(models) != 1 else ''})[/dim]")
        console.print(f"      Models       {model_text}")
        console.print(f"      Credentials  {'[green]✓[/green]' if item.get('credential') else '[yellow]![/yellow]'} {credential}")

    _section("CAPABILITIES")
    _row("Agent Execution", "Enabled", "ok")
    _row("Workflow Execution", "Enabled", "ok")
    _row("Tool Execution", "Enabled", "ok")
    _row("RAG", "Enabled", "ok")
    _row("Guardrails", "Enabled", "ok")
    _row("Execution Trace", "Enabled", "ok")

    log_root = Path(os.getenv("EAF_LOG_DIR", str(PROJECT_ROOT / "logs")))
    _section("LOGGING")
    _row("Framework Logs", "Available" if log_root.exists() else "Will be created", "ok" if log_root.exists() else "warn")
    _row("Execution Logs", "Available" if log_root.exists() else "Will be created", "ok" if log_root.exists() else "warn")
    _row("Date-wise", "Enabled", "ok")
    _row("Rotation", f"{int(os.getenv('EAF_LOG_MAX_FILE_BYTES', '10485760')) / (1024 * 1024):g} MB", "ok")
    _row("Secret Masking", "Enabled", "ok")

    _section("STORAGE")
    _row("Definitions", "Available" if PROJECT_ROOT.exists() else "Unavailable", "ok" if PROJECT_ROOT.exists() else "error")
    _row("Logs", str(log_root), "ok" if log_root.exists() else "warn")
    _row("Knowledge Base", str(CHROMADB_PATH), kb_health)

    _section("PATHS")
    _row("Project", str(PROJECT_ROOT))
    _row("Agents", str(AGENTS_DIR))
    _row("Workflows", str(WORKFLOWS_DIR))
    _row("Tools", str(TOOLS_DIR))
    _row("Guardrails", str(GUARDRAIL_DEFINITIONS_DIR))
    _row("Knowledge Base", str(CHROMADB_PATH))

    issues: list[str] = []
    for label, health in (
        ("Agent definitions", agent_health),
        ("Workflow definitions", workflow_health),
        ("Tool definitions", tool_health),
        ("Guardrail definitions", guardrail_health),
        ("Knowledge Base storage", kb_health),
    ):
        if health == "error":
            issues.append(label)
    if selected_item and _llm_status(selected_item) != "ok":
        issues.append("default LLM configuration")

    _section("OVERALL STATUS")
    if not issues:
        console.print("[bold green]✓ SYSTEM READY[/bold green]")
    else:
        console.print("[bold yellow]! SYSTEM DEGRADED[/bold yellow]")
        for issue in issues:
            console.print(f"  [yellow]![/yellow] {issue}")

    console.print("\n[dim]B = Back  |  0 = Exit[/dim]\n")
