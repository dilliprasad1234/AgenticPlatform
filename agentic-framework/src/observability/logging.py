"""Centralized two-level observability for the Enterprise Agent Framework.

Log layout
----------
logs/
  framework/
    YYYY-MM-DD/
      framework.log
      framework.log.1 ...
  executions/
    traces/
      YYYY-MM-DD/
        execution-<execution-id>.log
        execution-<execution-id>.log.1 ...
    agents/
      YYYY-MM-DD/
        <agent-id>/
          execution-<execution-id>.log
    workflows/
      YYYY-MM-DD/
        <workflow-id>/
          execution-<execution-id>.log
    guardrails/
      YYYY-MM-DD/
        <guardrail-id>/
          execution-<execution-id>.log
    tools/
      YYYY-MM-DD/
        <tool-id>/
          execution-<execution-id>.log
    rag/
      YYYY-MM-DD/
        <knowledge-base>/
          execution-<execution-id>.log

Framework logs remain date based. Every top-level run receives a unique
execution/trace ID, so separate runs never append to one another. The aggregate
trace contains the complete observable run, while component folders provide a
filtered view of the same run. Every execution file rotates independently at
10 MB.
"""
from __future__ import annotations

import contextvars
import logging
import os
import re
import traceback
import uuid
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

TRACE_ID = contextvars.ContextVar("eaf_trace_id", default="-")
SPAN_ID = contextvars.ContextVar("eaf_span_id", default="-")
RUN_DATE = contextvars.ContextVar("eaf_run_date", default=None)
_RUN_TOKENS = contextvars.ContextVar("eaf_run_tokens", default=None)

SECRET_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|cookie|credential|access[_-]?key)",
    re.IGNORECASE,
)
MAX_VALUE_LENGTH = int(os.getenv("EAF_LOG_MAX_VALUE_LENGTH", "12000"))
MAX_LOG_FILE_BYTES = int(os.getenv("EAF_LOG_MAX_FILE_BYTES", str(10 * 1024 * 1024)))
BACKUP_COUNT = int(os.getenv("EAF_LOG_BACKUP_COUNT", "20"))

FULL_CONTENT_KEYS = {
    "processed_content", "final_answer", "observation", "result",
    "output", "raw_output", "task_description", "description",
}

ANSI = {
    logging.DEBUG: "\033[34m",      # blue
    logging.INFO: "\033[32m",       # green
    logging.ERROR: "\033[31m",      # red
    logging.WARNING: "\033[33m",   # yellow
    logging.CRITICAL: "\033[31m",  # red
}
RESET = "\033[0m"

_COMPONENT_DIRS = {
    "agent": "agents",
    "agents": "agents",
    "workflow": "workflows",
    "workflows": "workflows",
    "guardrail": "guardrails",
    "guardrails": "guardrails",
    "tool": "tools",
    "tools": "tools",
    "rag": "rag",
    "kb": "rag",
    "knowledge_base": "rag",
}

_COMPONENT_ID_FIELDS = {
    "agent": ("agent_id", "agent_name"),
    "agents": ("agent_id", "agent_name"),
    "workflow": ("workflow_id", "workflow_name"),
    "workflows": ("workflow_id", "workflow_name"),
    "guardrail": ("guardrail_id", "guardrail_name"),
    "guardrails": ("guardrail_id", "guardrail_name"),
    "tool": ("tool_id", "tool_name"),
    "tools": ("tool_id", "tool_name"),
    "rag": ("knowledge_base", "collection", "kb_id", "kb_name"),
    "kb": ("knowledge_base", "collection", "kb_id", "kb_name"),
    "knowledge_base": ("knowledge_base", "collection", "kb_id", "kb_name"),
}


class _ColorFormatter(logging.Formatter):
    """Human-readable formatter with green/blue/red level colours."""

    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "payload", {}) or {}
        timestamp = datetime.fromtimestamp(record.created).isoformat(timespec="milliseconds")
        level = record.levelname
        colour = ANSI.get(record.levelno, "")
        trace_id = getattr(record, "trace_id", TRACE_ID.get())
        span_id = getattr(record, "span_id", SPAN_ID.get())
        text = (
            f"{timestamp} | {level:<8} | "
            f"trace={trace_id} | span={span_id} | "
            f"component={payload.get('component', '-')} | "
            f"event={payload.get('event', 'log')} | "
            f"{payload.get('message', record.getMessage())}"
        )
        return f"{colour}{text}{RESET}" if colour else text


def _sanitize(value: Any, key: str | None = None) -> Any:
    """Redact secrets and truncate unusually large values."""
    if key and SECRET_RE.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    if isinstance(value, str):
        if key and key.lower() in FULL_CONTENT_KEYS:
            return value
        return value if len(value) <= MAX_VALUE_LENGTH else value[:MAX_VALUE_LENGTH] + "...[TRUNCATED]"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)


def _new_id() -> str:
    return str(uuid.uuid4())


def _root() -> Path:
    return Path(os.getenv("EAF_LOG_DIR", str(Path.cwd() / "logs")))


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _safe_filename(value: Any) -> str:
    """Convert a runtime identity to a safe, readable filename."""
    value = str(value or "unknown").strip()
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    value = value.strip("._") or "unknown"
    return value[:180]


class _ExecutionTraceFormatter(logging.Formatter):
    """Render observable execution events in an AAVA-style readable format."""

    _HEADERS = {
        "execution_started": "🚀 Agent Execution Started",
        "task_started": "📝 Task Started",
        "tool_initialized": "🛠️ Tool Initialized",
        "tool_action": "▶️ Action",
        "tool_observation": "🔎 Observation",
        "decision": "💭 Decision Summary",
        "llm_started": "🤖 LLM Call Started",
        "llm_completed": "🤖 LLM Call Completed",
        "agent_finished": "✅ Agent Finished",
        "task_finished": "✅ Task Finished",
        "execution_completed": "🏁 Execution Completed",
        "workflow_started": "🚀 Workflow Execution Started",
        "workflow_step_started": "🧩 Workflow Step Started",
        "workflow_step_completed": "✅ Workflow Step Completed",
        "workflow_completed": "🏁 Workflow Execution Completed",
        "workflow_failed": "❌ Workflow Execution Failed",
        "tool_started": "🛠️ Tool Execution Started",
        "tool_completed": "✅ Tool Execution Completed",
        "tool_failed": "❌ Tool Execution Failed",
        "rag_started": "📚 RAG Execution Started",
        "rag_retrieval_started": "🔎 RAG Retrieval Started",
        "rag_retrieval_completed": "📖 RAG Retrieval Completed",
        "rag_completed": "🏁 RAG Execution Completed",
        "rag_failed": "❌ RAG Execution Failed",
        "guardrail_started": "🛡️ Guardrail Execution Started",
        "guardrail_completed": "✅ Guardrail Execution Completed",
        "guardrail_failed": "❌ Guardrail Execution Failed",
    }

    _FIELDS = {
        "execution_started": ("Agent", "agent_name", "Agent ID", "agent_id", "Description", "description", "Expected Output", "expected_output"),
        "task_started": ("Agent", "agent_name", "Task Prompt", "task_description", "Expected Output", "expected_output"),
        "tool_initialized": ("Tool", "tool_name", "Tool ID", "tool_id", "Agent", "agent_name", "Tool Class", "tool_class", "Tool Arguments", "arguments"),
        "tool_action": ("Tool", "tool_name", "Tool ID", "tool_id", "Agent", "agent_name", "Action", "action", "Action Input", "action_input"),
        "tool_observation": ("Tool", "tool_name", "Status", "status", "Observation", "observation"),
        "decision": ("Agent", "agent_name", "Decision", "decision", "Reason", "reason"),
        "llm_started": ("Agent", "agent_name", "Provider", "provider", "Model", "model"),
        "llm_completed": ("Agent", "agent_name"),
        "agent_finished": ("Agent", "agent_name", "Final Answer", "final_answer"),
        "task_finished": ("Agent", "agent_name", "Status", "status", "Final Answer", "final_answer"),
        "execution_completed": ("Agent", "agent_name", "Status", "status", "Final Answer", "final_answer"),
        "workflow_started": ("Workflow", "workflow_name", "Workflow ID", "workflow_id", "Input", "user_input"),
        "workflow_step_started": ("Workflow", "workflow_name", "Step ID", "step_id", "Step Type", "step_type"),
        "workflow_step_completed": ("Workflow", "workflow_name", "Step ID", "step_id", "Status", "status", "Result", "result"),
        "workflow_completed": ("Workflow", "workflow_name", "Workflow ID", "workflow_id", "Status", "status", "Final Result", "result"),
        "workflow_failed": ("Workflow", "workflow_name", "Workflow ID", "workflow_id", "Error Type", "error_type", "Error", "error"),
        "tool_started": ("Tool", "tool_name", "Tool ID", "tool_id", "Agent", "agent_name", "Arguments", "arguments"),
        "tool_completed": ("Tool", "tool_name", "Tool ID", "tool_id", "Status", "status", "Result", "result"),
        "tool_failed": ("Tool", "tool_name", "Tool ID", "tool_id", "Error Type", "error_type", "Error", "error"),
        "rag_started": ("Knowledge Base", "knowledge_base", "Query", "query", "Top K", "top_k"),
        "rag_retrieval_started": ("Knowledge Base", "knowledge_base", "Query", "query", "Top K", "top_k"),
        "rag_retrieval_completed": ("Knowledge Base", "knowledge_base", "Result Count", "result_count", "Results", "result"),
        "rag_completed": ("Knowledge Base", "knowledge_base", "Status", "status", "Result Count", "result_count"),
        "rag_failed": ("Knowledge Base", "knowledge_base", "Error Type", "error_type", "Error", "error"),
        "guardrail_started": ("Guardrail", "guardrail_name", "Guardrail ID", "guardrail_id", "Phase", "phase", "Input", "value"),
        "guardrail_completed": ("Guardrail", "guardrail_name", "Guardrail ID", "guardrail_id", "Status", "status", "Passed", "passed", "Result", "result"),
        "guardrail_failed": ("Guardrail", "guardrail_name", "Guardrail ID", "guardrail_id", "Error Type", "error_type", "Error", "error"),
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "payload", {}) or {}
        view = payload.get("trace_view")
        if not view:
            return _plain_line(record)
        timestamp = datetime.fromtimestamp(record.created).isoformat(timespec="milliseconds")
        trace_id = getattr(record, "trace_id", "-")
        span_id = getattr(record, "span_id", "-")
        lines = ["", self._HEADERS.get(view, view), "─" * 72,
                 f"Timestamp: {timestamp}", f"Execution ID: {trace_id}", f"Span ID: {span_id}"]
        fields = self._FIELDS.get(view, ())
        for i in range(0, len(fields), 2):
            label, key = fields[i], fields[i + 1]
            if key not in payload or payload[key] in (None, ""):
                continue
            value = payload[key]
            if isinstance(value, (dict, list, tuple)):
                import json as _json
                value = _json.dumps(value, indent=2, ensure_ascii=False, default=str)
            lines.append(f"{label}: {value}")
        lines.append("")
        return "\n".join(lines)


def _plain_line(record: logging.LogRecord) -> str:
    payload = getattr(record, "payload", {}) or {}
    timestamp = datetime.fromtimestamp(record.created).isoformat(timespec="milliseconds")
    return (f"{timestamp} | {record.levelname:<8} | trace={getattr(record, 'trace_id', '-')} | "
            f"span={getattr(record, 'span_id', '-')} | component={payload.get('component', '-')} | "
            f"event={payload.get('event', 'log')} | {payload.get('message', record.getMessage())}")


class _FrameworkFilter(logging.Filter):
    """Keep framework logs at framework scope."""

    def filter(self, record: logging.LogRecord) -> bool:
        payload = getattr(record, "payload", {}) or {}
        return payload.get("component") == "framework" or getattr(record, "trace_id", "-") == "-"


class _DailySizeRotatingHandler(RotatingFileHandler):
    """10 MB rotating handler that automatically switches to a new date folder."""

    def __init__(self, root: Path, filename: str, level: int = logging.DEBUG):
        self._root = root
        self._filename = filename
        self._date = _today()
        path = root / self._date / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(
            path,
            maxBytes=MAX_LOG_FILE_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        self.setLevel(level)
        self.setFormatter(_ColorFormatter())

    def emit(self, record: logging.LogRecord) -> None:
        current_date = _today()
        if current_date != self._date:
            self.acquire()
            try:
                if self.stream:
                    self.stream.flush()
                    self.stream.close()
                    self.stream = None
                self._date = current_date
                self.baseFilename = os.path.abspath(self._root / current_date / self._filename)
                Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True)
                self.stream = self._open()
            finally:
                self.release()
        super().emit(record)


def _handler(path: Path, level: int = logging.DEBUG, *, execution_trace: bool = False) -> RotatingFileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=MAX_LOG_FILE_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(_ExecutionTraceFormatter() if execution_trace else _ColorFormatter())
    return handler


def configure_logging() -> None:
    """Configure the framework logger once per process."""
    logger = logging.getLogger("eaf")
    if getattr(logger, "_eaf_configured", False):
        return

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger._eaf_log_root = _root()

    framework_handler = _DailySizeRotatingHandler(_root() / "framework", "framework.log")
    framework_handler.addFilter(_FrameworkFilter())
    logger.addHandler(framework_handler)

    console_level = getattr(
        logging,
        os.getenv("EAF_CONSOLE_LOG_LEVEL", "INFO").upper(),
        logging.INFO,
    )
    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(_ColorFormatter())
    logger.addHandler(console)

    logger._eaf_configured = True


def _execution_identity(component: str, payload: dict[str, Any]) -> str:
    component_name = str(component).lower()
    for field in _COMPONENT_ID_FIELDS.get(component_name, ()):
        value = payload.get(field)
        if value not in (None, ""):
            return _safe_filename(value)
    return _safe_filename(payload.get("name") or payload.get("run_name") or component_name)


def _execution_paths(trace_id: str, component: str, payload: dict[str, Any]) -> tuple[Path, Path]:
    """Return aggregate per-run trace path and component-specific per-run path."""
    date = RUN_DATE.get() or _today()
    identity = _execution_identity(component, payload)
    run_file = _root() / "executions" / "traces" / date / f"execution_{_safe_filename(trace_id)}.log"
    component_dir = _COMPONENT_DIRS.get(str(component).lower(), "other")
    component_file = _root() / "executions" / component_dir / date / identity / f"execution_{_safe_filename(trace_id)}.log"
    return run_file, component_file


def _execution_record(level: int, payload: dict[str, Any]) -> logging.LogRecord:
    logger = logging.getLogger("eaf")
    record = logger.makeRecord(logger.name, level, fn="", lno=0,
                               msg=payload.get("message") or payload.get("event"), args=(), exc_info=None)
    record.payload = payload
    record.trace_id = TRACE_ID.get()
    record.span_id = SPAN_ID.get()
    return record


def log_event(level: int | str, event: str, *, component: str, message: str = "", **fields: Any) -> None:
    """Write an event to framework logging and, during a run, isolated execution files."""
    configure_logging()
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    payload = _sanitize({"event": event, "component": component, "message": message, **fields})
    logger = logging.getLogger("eaf")
    record = logger.makeRecord(logger.name, level, fn="", lno=0, msg=message or event, args=(), exc_info=None)
    record.payload = payload
    record.trace_id = TRACE_ID.get()
    record.span_id = SPAN_ID.get()
    logger.handle(record)

    trace_id = TRACE_ID.get()
    # Framework events belong only to the framework log. Execution files contain
    # observable runtime events from agent/workflow/tool/RAG/guardrail components.
    if trace_id == "-" or str(component).lower() == "framework":
        return

    try:
        run_file, component_file = _execution_paths(trace_id, component, payload)
        exec_record = _execution_record(level, {"timestamp": datetime.now().isoformat(),
                                                "level": logging.getLevelName(level),
                                                "trace_id": trace_id, "span_id": SPAN_ID.get(), **payload})
        _write_to_file(run_file, exec_record)
        if component_file != run_file:
            _write_to_file(component_file, exec_record)
    except OSError:
        # Observability must never stop application execution.
        pass


def _write_to_file(path: Path, record: logging.LogRecord) -> None:
    """Write one event using an independently rotating 10 MB file."""
    handler = _handler(path, execution_trace=True)
    try:
        handler.emit(record)
    finally:
        handler.close()


def start_run(*, run_type: str, name: str, **fields: Any) -> str:
    """Start a top-level execution and establish its correlation context."""
    trace_id = _new_id()
    trace_token = TRACE_ID.set(trace_id)
    span_token = SPAN_ID.set(_new_id())
    date_token = RUN_DATE.set(_today())
    _RUN_TOKENS.set((trace_token, span_token, date_token))

    log_event(
        "INFO",
        "run.started",
        component="framework",
        message=f"{run_type} started: {name}",
        run_type=run_type,
        run_name=name,
        start_time=datetime.now().isoformat(),
        **fields,
    )
    return trace_id


def end_run(*, status: str, **fields: Any) -> None:
    """Complete the current top-level execution and clear its context."""
    success = status.lower() == "success"
    log_event(
        "INFO" if success else "ERROR",
        "run.completed" if success else "run.failed",
        component="framework",
        message=f"Run completed with status={status}",
        status=status,
        end_time=datetime.now().isoformat(),
        **fields,
    )

    tokens = _RUN_TOKENS.get()
    if tokens:
        trace_token, span_token, date_token = tokens
        try:
            TRACE_ID.reset(trace_token)
            SPAN_ID.reset(span_token)
            RUN_DATE.reset(date_token)
        finally:
            _RUN_TOKENS.set(None)
    else:
        TRACE_ID.set("-")
        SPAN_ID.set("-")
        RUN_DATE.set(None)


@contextmanager
def span(name: str, *, component: str, **fields: Any) -> Iterator[str]:
    """Create a nested execution span with duration and errors."""
    parent_span = SPAN_ID.get()
    span_id = _new_id()
    token = SPAN_ID.set(span_id)
    started = perf_counter()
    log_event(
        "DEBUG",
        "span.started",
        component=component,
        message=f"Started {name}",
        span_name=name,
        parent_span_id=parent_span,
        **fields,
    )
    try:
        yield span_id
    except Exception as exc:
        log_event(
            "ERROR",
            "span.failed",
            component=component,
            message=f"Failed {name}: {exc}",
            span_name=name,
            duration_ms=round((perf_counter() - started) * 1000, 3),
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
            **fields,
        )
        raise
    else:
        log_event(
            "DEBUG",
            "span.completed",
            component=component,
            message=f"Completed {name}",
            span_name=name,
            duration_ms=round((perf_counter() - started) * 1000, 3),
            **fields,
        )
    finally:
        SPAN_ID.reset(token)


def log_exception(event: str, *, component: str, exc: BaseException, **fields: Any) -> None:
    """Persist a complete application exception."""
    log_event(
        "ERROR",
        event,
        component=component,
        message=str(exc),
        error_type=type(exc).__name__,
        error=str(exc),
        traceback=traceback.format_exc(),
        **fields,
    )
