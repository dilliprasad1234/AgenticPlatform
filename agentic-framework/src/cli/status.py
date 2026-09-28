"""Framework readiness/status display for the CLI."""
import os
import sys
from pathlib import Path

from src.config import AGENTS_DIR, TOOLS_DIR, WORKFLOWS_DIR, CHROMADB_PATH
from src.cli.ui import console, success, error


def show_status() -> None:
    console.print("\n[bold]System Status[/bold]\n")
    checks = []
    checks.append(("Python", sys.version.split()[0], True))
    for label, value in [
        ("Agents directory", AGENTS_DIR),
        ("Workflows directory", WORKFLOWS_DIR),
        ("Tools directory", TOOLS_DIR),
        ("ChromaDB path", CHROMADB_PATH),
    ]:
        p = Path(value)
        checks.append((label, str(p), p.exists()))
    for provider, env in [("Gemini", "GEMINI_API_KEY"), ("OpenAI", "OPENAI_API_KEY"), ("Anthropic", "ANTHROPIC_API_KEY")]:
        configured = bool(os.getenv(env))
        checks.append((f"{provider} API key", "configured" if configured else "not configured", configured))
    checks.append(("Ollama model", os.getenv("OLLAMA_MODEL", "not configured"), bool(os.getenv("OLLAMA_MODEL"))))
    for label, value, ok in checks:
        console.print(f"[green]✓[/green] {label}: {value}" if ok else f"[yellow]![/yellow] {label}: {value}")
    console.print()
