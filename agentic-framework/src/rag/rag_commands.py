"""Module containing rag commands functionality for the Enterprise Agent Framework."""

import typer
from src.cli.prompts import prompt
from src.cli.navigation import CLIBack, CLIExit
from src.rag import rag_actions as actions
from src.cli.ui import (
    error,
    menu,
)


def kb_menu():
    """Execute the kb menu operation."""
    while True:
        menu(
            "Knowledge Base",
            [
                "1. Create Knowledge Base",
                "2. View Knowledge Bases",
                "3. Add Document",
                "4. Remove a Document",
                "5. Delete a Knowledge Base",
            ],
            breadcrumb="Home > Knowledge Base",
            subtitle="Choose an action. Use B to go back one screen or 0 to exit.",
            module_navigation=True
        )
        choice = prompt("Select an option", navigation=False).strip()
        try:
            if choice == "1":
                actions.create()
            elif choice == "2":
                actions.list_all()
            elif choice == "3":
                actions.add_document()
            elif choice == "4":
                actions.remove_document()
            elif choice == "5":
                actions.delete()
            elif choice.lower() in {"b", "back"}:
                return

            elif choice.lower() in {"0", "x", "exit"}:
                raise CLIExit()
            else:
                error("Please choose one of the options above, B to go back one screen, or 0 to exit.")
        except CLIBack:
            return
        except CLIExit:
            raise
        except Exception as exc:
            error(str(exc))