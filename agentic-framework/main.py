"""Interactive command-line entry point for the Enterprise Agent Framework."""

import typer
from rich.console import Console

from src.cli.greeting import get_welcome_message
from src.cli.ui import error
from src.cli.prompts import prompt
from src.cli.navigation import CLIBack, CLIExit
from src.cli.help import show_help
from src.cli.system_status import show_system_status
from src.exceptions import FrameworkError, handle_unexpected_exception
from src.observability import configure_logging, log_event, log_exception

from agents.agent_commands import agent_menu
from tools.tool_commands import tool_menu
from workflows.workflow_commands import workflow_menu

import sys

# Ensure UTF-8 output on Windows terminals.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from guardrails.guardrail_cli import guardrail_menu
from src.rag.rag_commands import kb_menu


console = Console()


def main_menu() -> None:
    """Display the main framework menu and route user actions safely."""
    configure_logging()
    log_event(
        "INFO",
        "framework.started",
        component="framework",
        message="Enterprise Agent Framework CLI started.",
    )

    typer.echo(get_welcome_message())

    while True:
        console.print()
        console.print("[bold cyan]Main Menu[/bold cyan]")
        console.print("[dim]Choose an area to get started.[/dim]")
        console.print()
        console.print("  1. Agents")
        console.print("  2. Workflows")
        console.print("  3. Tools")
        console.print("  4. Guardrails")
        console.print("  5. Knowledge Base")
        console.print("  6. System Status")
        console.print("  7. Help")
        console.print("  0. Exit")
        console.print()

        try:
            choice = prompt("Select an option", navigation=False).strip()
            log_event(
                "DEBUG",
                "cli.menu_selection",
                component="framework",
                message=f"Main menu option selected: {choice}",
                menu="main",
                choice=choice,
            )

            if choice == "1":
                agent_menu()
            elif choice == "2":
                workflow_menu()
            elif choice == "3":
                tool_menu()
            elif choice == "4":
                guardrail_menu()
            elif choice == "5":
                kb_menu()
            elif choice == "6":
                show_system_status()
            elif choice == "7":
                show_help()
            elif choice == "0":
                log_event(
                    "INFO",
                    "framework.stopped",
                    component="framework",
                    message="CLI shutdown requested.",
                )
                typer.echo("Exiting...")
                return
            else:
                error("Please select a number from 0 to 7.")
        except CLIBack:
            error("You are already at the Main Menu. Select an option above.")
        except CLIExit:
            log_event(
                "INFO",
                "framework.stopped",
                component="framework",
                message="CLI exit requested.",
            )
            typer.echo("Exiting...")
            return
        except typer.Abort as exc:
            log_exception("cli.aborted", component="framework", exc=exc)
            typer.secho("\\nOperation aborted.", fg=typer.colors.YELLOW)
        except FrameworkError as exc:
            log_exception(
                "framework.handled_error",
                component="framework",
                exc=exc,
                operation="main_menu",
            )
            error(exc.user_message)
        except Exception as exc:
            handle_unexpected_exception(
                exc,
                operation="main_menu",
                choice=locals().get("choice"),
            )
            error("An unexpected framework error occurred. Check the logs for details.")


def main() -> None:
    """Start the Enterprise Agent Framework directly in the main CLI menu."""
    try:
        main_menu()
    except KeyboardInterrupt:
        log_event(
            "INFO",
            "framework.interrupted",
            component="framework",
            message="Framework interrupted by user.",
        )
        typer.secho("\\nFramework interrupted. Exiting safely.", fg=typer.colors.YELLOW)
    except Exception as exc:
        handle_unexpected_exception(exc, operation="application_startup")
        typer.secho(
            "\\nA critical framework error occurred. Check the framework logs for details.",
            fg=typer.colors.RED,
        )


if __name__ == "__main__":
    main()
