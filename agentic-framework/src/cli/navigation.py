"""Shared CLI navigation controls.

The CLI uses contextual navigation. Menus use numbered options; deep interactive prompts accept B (Back) and 0 (Exit).
"""

from __future__ import annotations


class CLINavigation(Exception):
    """Base exception for non-error CLI navigation actions."""

    def __init__(self, action: str):
        self.action = action
        super().__init__(action)


class CLIBack(CLINavigation):
    def __init__(self):
        super().__init__("back")


class CLIExit(CLINavigation):
    def __init__(self):
        super().__init__("exit")


NAVIGATION_HELP = "B = Back  |  0 = Exit"


def raise_navigation(value: str) -> None:
    """Raise the navigation action represented by *value* if applicable."""
    command = value.strip().lower()
    if command in {"b", "back"}:
        raise CLIBack()
    if command in {"0", "x", "exit", "quit"}:
        raise CLIExit()
