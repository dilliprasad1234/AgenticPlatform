"""Reusable exception hierarchy and centralized exception handling."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from src.observability import log_exception

__all__ = [
    "AgentError",
    "ArtifactNotFoundError",
    "ConfigurationError",
    "ExecutionError",
    "FrameworkError",
    "GuardrailError",
    "LLMError",
    "RAGError",
    "ToolError",
    "ValidationError",
    "WorkflowError",
    "exception_handler",
    "handle_framework_exception",
    "handle_llm_call",
    "handle_unexpected_exception",
    "parse_llm_json",
    "translate_runtime_error",
    "validate_llm_content",
    "validate_rag_file_size",
]


# ============================================================
# BASE FRAMEWORK EXCEPTIONS
# ============================================================


class FrameworkError(Exception):
    """Base exception for all expected framework errors."""

    def __init__(
        self,
        message: str = "A framework error occurred.",
        *,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.details: dict[str, Any] = details or {}

        # Prevent duplicate logging when the same exception
        # passes through multiple framework handlers.
        self._framework_handled = False

    @property
    def _handled(self) -> bool:
        """Backward-compatible alias for _framework_handled."""
        return self._framework_handled

    @_handled.setter
    def _handled(self, value: bool) -> None:
        self._framework_handled = value

    def format_display(self) -> str:
        """Format a clear user-facing error message with details if present."""
        if not self.details:
            return self.user_message
        detail_lines = [f"  - {k}: {v}" for k, v in self.details.items()]
        return f"{self.user_message}\nDetails:\n" + "\n".join(detail_lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception context to a structured dictionary for serialization."""
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"message={self.message!r}, "
            f"user_message={self.user_message!r}, "
            f"details={self.details!r})"
        )


class ConfigurationError(FrameworkError):
    """Raised when framework configuration is missing or invalid."""

    def __init__(
        self,
        message: str | None = None,
        *,
        config_key: str | None = None,
        config_path: str | None = None,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.config_key = config_key
        self.config_path = config_path

        extra_details = dict(details or {})
        if config_key:
            extra_details["config_key"] = config_key
        if config_path:
            extra_details["config_path"] = config_path

        if message is None:
            if config_key:
                message = f"Missing or invalid configuration for '{config_key}'."
            elif config_path:
                message = f"Configuration file at '{config_path}' is invalid or missing."
            else:
                message = "Framework configuration is missing or invalid."

        if user_message is None:
            if config_key and not message.startswith(f"Configuration error for '{config_key}'"):
                user_message = f"Configuration error for '{config_key}': {message}"
            else:
                user_message = message

        super().__init__(
            message,
            user_message=user_message,
            details=extra_details,
        )


class ArtifactNotFoundError(FrameworkError):
    """Raised when a framework artifact cannot be found."""

    def __init__(
        self,
        message: str | None = None,
        *,
        artifact_name: str | None = None,
        artifact_type: str | None = None,
        path: str | None = None,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.artifact_name = artifact_name
        self.artifact_type = artifact_type
        self.path = path

        extra_details = dict(details or {})
        if artifact_name:
            extra_details["artifact_name"] = artifact_name
        if artifact_type:
            extra_details["artifact_type"] = artifact_type
        if path:
            extra_details["path"] = path

        label = artifact_type.capitalize() if artifact_type else "Artifact"
        if message is None:
            if artifact_name and path:
                message = f"{label} '{artifact_name}' was not found at '{path}'."
            elif artifact_name:
                message = f"{label} '{artifact_name}' was not found."
            else:
                message = "Requested framework artifact was not found."

        if user_message is None:
            if artifact_name and not message.startswith(f"{label} '{artifact_name}'"):
                user_message = f"{label} '{artifact_name}' not found: {message}"
            else:
                user_message = message

        super().__init__(
            message,
            user_message=user_message,
            details=extra_details,
        )


class ValidationError(FrameworkError):
    """Raised when input or framework data fails validation."""

    def __init__(
        self,
        message: str | None = None,
        *,
        field: str | None = None,
        value: Any = None,
        errors: list[Any] | None = None,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.field = field
        self.value = value
        self.errors = errors or []

        extra_details = dict(details or {})
        if field:
            extra_details["field"] = field
        if value is not None:
            extra_details["value"] = str(value)
        if errors:
            extra_details["errors"] = errors

        if message is None:
            if field:
                message = f"Validation failed for field '{field}'."
            else:
                message = "Validation failed for input or framework data."

        if user_message is None:
            if field and not message.startswith(f"Validation failed for field '{field}'"):
                user_message = f"Validation failed for field '{field}': {message}"
            else:
                user_message = message

        super().__init__(
            message,
            user_message=user_message,
            details=extra_details,
        )


class ExecutionError(FrameworkError):
    """Raised when execution of a framework component fails."""

    def __init__(
        self,
        message: str = "Framework execution failed.",
        *,
        component: str | None = None,
        operation: str | None = None,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.component = component
        self.operation = operation

        extra_details = dict(details or {})
        if component:
            extra_details["component"] = component
        if operation:
            extra_details["operation"] = operation

        if user_message is None:
            if component and operation:
                user_message = f"Execution failed in {component} during '{operation}': {message}"
            elif component:
                user_message = f"Execution failed in {component}: {message}"
            else:
                user_message = message

        super().__init__(
            message,
            user_message=user_message,
            details=extra_details,
        )


# ============================================================
# DOMAIN-SPECIFIC EXECUTION EXCEPTIONS
# ============================================================


class AgentError(ExecutionError):
    """Raised when an agent operation fails."""

    def __init__(
        self,
        message: str | None = None,
        *,
        agent_name: str | None = None,
        task_id: str | None = None,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.task_id = task_id

        extra_details = dict(details or {})
        if agent_name:
            extra_details["agent_name"] = agent_name
        if task_id:
            extra_details["task_id"] = task_id

        if message is None:
            if agent_name:
                message = f"Agent '{agent_name}' execution failed."
            else:
                message = "Agent execution failed."

        if user_message is None:
            if agent_name and not message.startswith(f"Agent '{agent_name}'"):
                user_message = f"Agent '{agent_name}' failed: {message}"
            else:
                user_message = message

        super().__init__(
            message,
            component="agent",
            user_message=user_message,
            details=extra_details,
        )


class ToolError(ExecutionError):
    """Raised when a tool operation fails."""

    def __init__(
        self,
        message: str | None = None,
        *,
        tool_name: str | None = None,
        tool_input: dict[str, Any] | None = None,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.tool_input = tool_input

        extra_details = dict(details or {})
        if tool_name:
            extra_details["tool_name"] = tool_name
        if tool_input:
            extra_details["tool_input"] = tool_input

        if message is None:
            if tool_name:
                message = f"Tool '{tool_name}' execution failed."
            else:
                message = "Tool execution failed."

        if user_message is None:
            if tool_name and not message.startswith(f"Tool '{tool_name}'"):
                user_message = f"Tool '{tool_name}' failed: {message}"
            else:
                user_message = message

        super().__init__(
            message,
            component="tool",
            user_message=user_message,
            details=extra_details,
        )


class WorkflowError(ExecutionError):
    """Raised when a workflow operation fails."""

    def __init__(
        self,
        message: str | None = None,
        *,
        workflow_name: str | None = None,
        step: str | None = None,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.workflow_name = workflow_name
        self.step = step

        extra_details = dict(details or {})
        if workflow_name:
            extra_details["workflow_name"] = workflow_name
        if step:
            extra_details["step"] = step

        if message is None:
            if workflow_name and step:
                message = f"Workflow '{workflow_name}' failed at step '{step}'."
            elif workflow_name:
                message = f"Workflow '{workflow_name}' execution failed."
            else:
                message = "Workflow execution failed."

        if user_message is None:
            if workflow_name and step:
                user_message = f"Workflow '{workflow_name}' failed at step '{step}': {message}"
            elif workflow_name and not message.startswith(f"Workflow '{workflow_name}'"):
                user_message = f"Workflow '{workflow_name}' failed: {message}"
            else:
                user_message = message

        super().__init__(
            message,
            component="workflow",
            user_message=user_message,
            details=extra_details,
        )


class GuardrailError(FrameworkError):
    """Raised when a guardrail blocks an operation."""

    def __init__(
        self,
        message: str | None = None,
        *,
        guardrail_name: str | None = None,
        action: str | None = None,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.guardrail_name = guardrail_name
        self.action = action

        extra_details = dict(details or {})
        if guardrail_name:
            extra_details["guardrail_name"] = guardrail_name
        if action:
            extra_details["action"] = action

        if message is None:
            if guardrail_name:
                message = f"Guardrail '{guardrail_name}' blocked the operation."
            else:
                message = "Operation was blocked by guardrail policy."

        if user_message is None:
            if guardrail_name and not message.startswith(f"Guardrail '{guardrail_name}'"):
                user_message = f"Guardrail '{guardrail_name}' blocked operation: {message}"
            else:
                user_message = message

        super().__init__(
            message,
            user_message=user_message,
            details=extra_details,
        )


class RAGError(ExecutionError):
    """Raised when a RAG or knowledge-base operation fails."""

    def __init__(
        self,
        message: str | None = None,
        *,
        knowledge_base: str | None = None,
        query: str | None = None,
        filename: str | None = None,
        file_size_bytes: int | None = None,
        max_size_bytes: int | None = None,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.query = query
        self.filename = filename
        self.file_size_bytes = file_size_bytes
        self.max_size_bytes = max_size_bytes

        extra_details = dict(details or {})
        if knowledge_base:
            extra_details["knowledge_base"] = knowledge_base
        if query:
            extra_details["query"] = query
        if filename:
            extra_details["filename"] = filename
        if file_size_bytes is not None:
            extra_details["file_size_bytes"] = file_size_bytes
        if max_size_bytes is not None:
            extra_details["max_size_bytes"] = max_size_bytes

        if message is None:
            if filename and file_size_bytes is not None and max_size_bytes is not None:
                actual_mb = file_size_bytes / (1024 * 1024)
                max_mb = max_size_bytes / (1024 * 1024)
                message = (
                    f"File '{filename}' ({actual_mb:.2f} MB) exceeds maximum allowed size "
                    f"of {max_mb:.2f} MB."
                )
            elif filename and file_size_bytes == 0:
                message = f"File '{filename}' is empty (0 bytes). Cannot index empty documents."
            elif knowledge_base:
                message = f"Knowledge base '{knowledge_base}' operation failed."
            else:
                message = "RAG operation failed."

        if user_message is None:
            if knowledge_base and not message.startswith(f"Knowledge base '{knowledge_base}'"):
                user_message = f"Knowledge base '{knowledge_base}' failed: {message}"
            else:
                user_message = message

        super().__init__(
            message,
            component="rag",
            user_message=user_message,
            details=extra_details,
        )


class LLMError(ExecutionError):
    """Raised when an LLM cannot be initialized or invoked."""

    def __init__(
        self,
        message: str | None = None,
        *,
        provider: str | None = None,
        model: str | None = None,
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.provider = provider
        self.model = model

        extra_details = dict(details or {})
        if provider:
            extra_details["provider"] = provider
        if model:
            extra_details["model"] = model

        if message is None:
            if provider and model:
                message = f"{provider} model '{model}' operation failed."
            elif provider:
                message = f"{provider} operation failed."
            else:
                message = "LLM operation failed."

        if user_message is None:
            if provider and model and not message.startswith(f"{provider} model '{model}'"):
                user_message = f"{provider} model '{model}' failed: {message}"
            elif provider and not message.startswith(f"{provider}"):
                user_message = f"{provider} failed: {message}"
            else:
                user_message = message

        super().__init__(
            message,
            component="llm",
            user_message=user_message,
            details=extra_details,
        )


# ============================================================
# COMMON EXCEPTION HANDLING
# ============================================================


def handle_framework_exception(
    exc: FrameworkError,
    *,
    operation: str,
    **context: Any,
) -> None:
    """
    Centrally handle an expected framework exception.

    The exception is logged only once, even if the same exception
    passes through multiple framework handlers. Merges structured
    exception details into the logging context.
    """
    if getattr(exc, "_framework_handled", False) or getattr(exc, "_handled", False):
        return

    merged_context = {**getattr(exc, "details", {}), **context}
    component = merged_context.pop(
        "component",
        getattr(exc, "component", "framework") or "framework",
    )

    log_exception(
        "framework.handled_error",
        component=component,
        exc=exc,
        operation=operation,
        **merged_context,
    )

    try:
        exc._framework_handled = True
    except (AttributeError, TypeError):
        pass


def handle_unexpected_exception(
    exc: Exception,
    *,
    operation: str,
    **context: Any,
) -> None:
    """
    Centrally handle an unexpected exception.

    The exception is logged only once, even if the same exception
    passes through multiple framework handlers.
    """
    if getattr(exc, "_framework_handled", False):
        return

    ctx = dict(context)
    component = ctx.pop("component", "framework")

    log_exception(
        "framework.unhandled_exception",
        component=component,
        exc=exc,
        operation=operation,
        **ctx,
    )

    try:
        exc._framework_handled = True
    except (AttributeError, TypeError):
        pass


F = TypeVar("F", bound=Callable[..., Any])


def exception_handler(
    operation: str,
) -> Callable[[F], F]:
    """
    Reusable centralized exception handling decorator.

    Expected FrameworkError exceptions are logged centrally
    and re-raised unchanged.

    Unexpected exceptions are logged centrally and converted
    into ExecutionError so callers receive a consistent
    framework-level exception. Supports both synchronous and
    asynchronous functions.
    """

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(
                *args: Any,
                **kwargs: Any,
            ) -> Any:
                try:
                    return await func(
                        *args,
                        **kwargs,
                    )
                except FrameworkError as exc:
                    handle_framework_exception(
                        exc,
                        operation=operation,
                    )
                    raise
                except Exception as exc:
                    handle_unexpected_exception(
                        exc,
                        operation=operation,
                    )
                    raise ExecutionError(
                        f"{operation} failed: {exc}",
                        user_message=f"{operation} failed: {exc}",
                    ) from exc

            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def wrapper(
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            try:
                return func(
                    *args,
                    **kwargs,
                )
            except FrameworkError as exc:
                handle_framework_exception(
                    exc,
                    operation=operation,
                )
                raise
            except Exception as exc:
                handle_unexpected_exception(
                    exc,
                    operation=operation,
                )
                raise ExecutionError(
                    f"{operation} failed: {exc}",
                    user_message=f"{operation} failed: {exc}",
                ) from exc

        return wrapper  # type: ignore[return-value]

    return decorator


# ============================================================
# LLM HANDLING
# ============================================================


def handle_llm_call(
    operation: str,
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Execute an LLM operation and normalize unexpected failures.

    Existing LLMError exceptions are preserved.
    Other exceptions are converted into LLMError with underlying error details.
    """
    try:
        return func(
            *args,
            **kwargs,
        )
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(
            f"{operation} failed: {exc}",
            user_message=f"{operation} failed: {exc}",
        ) from exc


def validate_llm_content(
    content: str | None,
    provider: str,
) -> str:
    """
    Validate text returned by an LLM provider.

    Raises LLMError when the provider returns no content or empty whitespace.
    """
    if not content or not content.strip():
        raise LLMError(
            f"{provider} returned an empty response.",
            user_message=f"{provider} returned an empty response.",
        )

    return content


def _strip_markdown_json(content: str) -> str:
    """Strip markdown code block markers from LLM output if present."""
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def parse_llm_json(
    content: str | None,
    provider: str,
) -> dict[str, Any]:
    """
    Validate and parse JSON returned by an LLM provider.

    This centralizes empty-response, markdown stripping, and JSON parsing
    errors for all LLM providers.
    """
    content = validate_llm_content(
        content,
        provider,
    )
    cleaned_content = _strip_markdown_json(content)

    try:
        result = json.loads(
            cleaned_content
        )
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"{provider} returned invalid JSON.",
            user_message=f"{provider} returned an invalid response.",
        ) from exc

    if not isinstance(
        result,
        dict,
    ):
        raise LLMError(
            f"{provider} returned JSON that is not an object.",
            user_message=f"{provider} returned an invalid response.",
        )

    return result


# ============================================================
# RAG VALIDATION
# ============================================================


def validate_rag_file_size(
    filepath: Path | str,
    *,
    max_size_mb: float = 10.0,
    knowledge_base: str | None = None,
) -> Path:
    """
    Validate that a file exists, is a regular file, is non-empty, and does not exceed max_size_mb.

    Raises RAGError with structured domain metadata if validation fails.
    Returns the resolved Path object on success.
    """
    path = Path(filepath)
    filename = path.name

    if not path.exists():
        raise RAGError(
            f"File not found: '{path}'.",
            knowledge_base=knowledge_base,
            filename=filename,
            user_message=f"File not found: {path}",
        )

    if not path.is_file():
        raise RAGError(
            f"Path is not a regular file: '{path}'.",
            knowledge_base=knowledge_base,
            filename=filename,
            user_message=f"Path is not a regular file: {path}",
        )

    try:
        size_bytes = path.stat().st_size
    except OSError as exc:
        raise RAGError(
            f"Could not read file size for '{filename}': {exc}",
            knowledge_base=knowledge_base,
            filename=filename,
            user_message=f"Could not access file '{filename}'.",
        ) from exc

    if size_bytes == 0:
        raise RAGError(
            knowledge_base=knowledge_base,
            filename=filename,
            file_size_bytes=0,
            user_message=f"File '{filename}' is empty (0 bytes). Cannot index empty documents.",
        )

    max_bytes = int(max_size_mb * 1024 * 1024)
    if size_bytes > max_bytes:
        actual_mb = size_bytes / (1024 * 1024)
        raise RAGError(
            knowledge_base=knowledge_base,
            filename=filename,
            file_size_bytes=size_bytes,
            max_size_bytes=max_bytes,
            user_message=(
                f"File '{filename}' ({actual_mb:.2f} MB) exceeds maximum allowed size "
                f"of {max_size_mb:.1f} MB. Please upload a smaller document."
            ),
        )

    return path


# ============================================================
# RUNTIME ERROR TRANSLATION
# ============================================================


def translate_runtime_error(
    exc: Exception,
    *,
    default_message: str | None = None,
) -> str:
    """
    Translate low-level network, SSL, socket, auth, and database errors into actionable messages.

    Recognizes DNS failures, connection resets, TLS handshakes, authorization
    rejections, rate limits from external APIs/LLMs, and vector store batch limits.
    """
    err_str = str(exc)

    if "getaddrinfo failed" in err_str or "11001" in err_str:
        return (
            "Network connection failed: Unable to resolve LLM host. "
            "Please check your internet connection or configure a local model (Ollama) in .env for offline mode. "
            f"(Details: {exc})"
        )

    if "UNEXPECTED_EOF_WHILE_READING" in err_str or "EOF occurred" in err_str:
        return (
            "The LLM provider unexpectedly closed the connection during execution. "
            "This usually indicates an invalid API key, network proxy/firewall block, or provider outage. "
            f"(Details: {exc})"
        )

    if any(k in err_str for k in ("401", "Unauthorized", "API_KEY_INVALID", "invalid_api_key")):
        return (
            "Authentication failed: The configured API key was rejected by the LLM provider. "
            f"(Details: {exc})"
        )

    if any(k in err_str.lower() for k in ("429", "rate limit", "quota", "resource_exhausted")):
        return (
            "Rate limit or quota exceeded with the LLM provider. "
            f"(Details: {exc})"
        )

    if any(k in err_str.lower() for k in ("greater than max batch size", "too many sql variables", "batchsizeerror")):
        return (
            "Knowledge Base ingestion failed: Chunk batch size exceeds database limits. "
            "The document produced too many chunks for a single database transaction. "
            f"(Details: {exc})"
        )

    return default_message or f"Operation failed: {exc}"