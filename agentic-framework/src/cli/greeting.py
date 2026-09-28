"""Generate the framework CLI greeting using the local machine clock."""

import getpass
from datetime import datetime


def get_user_name() -> str:
    """Return the current operating-system username."""
    return getpass.getuser()


def get_greeting() -> str:
    """Return a time-appropriate greeting based on the local machine time."""
    current_hour = datetime.now().hour

    if current_hour < 12:
        return "Good Morning🌅"
    if current_hour < 17:
        return "Good Afternoon🌄"
    if current_hour < 21:
        return "Good Evening🌄"
    return "Good Night🌃"


def get_current_time() -> str:
    """Return the current local machine time formatted for the CLI."""
    return datetime.now().astimezone().strftime("%I:%M:%S %p")


def get_welcome_message() -> str:
    """Build the complete welcome banner with username, greeting, and local time."""
    user_name = get_user_name()
    greeting = get_greeting()
    current_time = get_current_time()

    return (
        "=============================================================\n"
        f"           Hello {user_name}👾!,{greeting}\n"
        f"              Current Time: {current_time}\n"
        "         What would you like to do today?\n"
        "Build, manage, and execute AI agents, tools, and workflows.\n"
        "============================================================="
    )
