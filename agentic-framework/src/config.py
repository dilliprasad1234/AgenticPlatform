"""Central configuration and filesystem paths for the framework."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Disable CrewAI/OpenTelemetry background telemetry by default.
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

PROJECT_ROOT = Path.cwd()

AGENTS_DIR = PROJECT_ROOT / "agents" / "definitions"

TOOLS_DIR = PROJECT_ROOT / "tools"
TOOL_DEFINITIONS_DIR = TOOLS_DIR / "definitions"
TOOL_IMPLEMENTATIONS_DIR = TOOLS_DIR / "implementations"

WORKFLOWS_DIR = PROJECT_ROOT / "workflows" / "definitions"

GUARDRAILS_DIR = PROJECT_ROOT / "guardrails"
GUARDRAIL_DEFINITIONS_DIR = GUARDRAILS_DIR / "definitions"
GUARDRAIL_IMPLEMENTATIONS_DIR = GUARDRAILS_DIR / "implementations"

RAG_INPUT_DIR = PROJECT_ROOT / "inputs" / "rag"
CHROMADB_PATH = Path(
    os.getenv("CHROMADB_PATH", str(PROJECT_ROOT / "data" / "chromadb"))
)
MAX_RAG_FILE_SIZE_MB = float(os.getenv("MAX_RAG_FILE_SIZE_MB", "10.0"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None

EDITOR = os.getenv("EDITOR", "auto")


def ensure_directories() -> None:
    """Create all framework-managed directories if they do not exist."""
    for directory in (
        AGENTS_DIR,
        WORKFLOWS_DIR,
        TOOL_DEFINITIONS_DIR,
        TOOL_IMPLEMENTATIONS_DIR,
        GUARDRAIL_DEFINITIONS_DIR,
        GUARDRAIL_IMPLEMENTATIONS_DIR,
        RAG_INPUT_DIR,
        CHROMADB_PATH,
    ):
        directory.mkdir(parents=True, exist_ok=True)
