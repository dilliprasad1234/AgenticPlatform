"""Clean prompt helpers with contextual B/0 navigation handling."""
from __future__ import annotations
from typing import Any
import typer
from contextvars import ContextVar
from src.cli.navigation import raise_navigation

_original_prompt = typer.prompt
_original_confirm = typer.confirm
_navigation_notice_shown: ContextVar[bool] = ContextVar("navigation_notice_shown", default=False)


def prompt(text: str, *args: Any, navigation: bool = True, **kwargs: Any) -> Any:
    """Prompt for input and process B/0 before type conversion.

    Navigation shortcuts are intentionally not printed beside every field.
    Screens/menus explain the available navigation once, keeping forms clean.
    """
    if not navigation:
        return _original_prompt(text, *args, **kwargs)

    requested_type = kwargs.pop("type", None)
    default = kwargs.pop("default", None)
    kwargs.pop("show_default", None)

    if not _navigation_notice_shown.get():
        typer.secho("Navigation: B = Back | 0 = Exit", fg=typer.colors.BRIGHT_BLACK)
        _navigation_notice_shown.set(True)

    while True:
        value = _original_prompt(
            text,
            *args,
            default="" if default is None else str(default),
            show_default=default is not None,
            **kwargs,
        )
        value = value if isinstance(value, str) else str(value)
        stripped = value.strip()

        if stripped:
            raise_navigation(stripped)
        if default is not None and not stripped:
            return default
        if requested_type is None or requested_type is str:
            return value
        try:
            return requested_type(value)
        except (TypeError, ValueError):
            typer.secho("Please enter a valid value.", fg=typer.colors.YELLOW)


def confirm(text: str, *args: Any, navigation: bool = True, **kwargs: Any) -> bool:
    """Confirmation prompt with B/0 support and no noisy inline shortcuts."""
    if not navigation:
        return _original_confirm(text, *args, **kwargs)
    default = kwargs.get("default", False)
    while True:
        value = _original_prompt(text, default="", show_default=False).strip().lower()
        if value in {"b", "back", "0", "x", "exit", "quit"}:
            raise_navigation(value)
        if value in {"y", "yes", "true", "1"}:
            return True
        if value in {"n", "no", "false", "0"}:
            return False
        if not value:
            return bool(default)
        typer.secho("Please enter Y or N.", fg=typer.colors.YELLOW)


def reset_navigation_notice() -> None:
    """Start a new guided operation so its navigation help is shown once."""
    _navigation_notice_shown.set(False)
