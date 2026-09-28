"""Built-in CLI help."""

from src.cli.ui import console


def show_help() -> None:
    """Display concise user-facing CLI guidance."""
    console.print("\n[bold]Enterprise Agent Framework — Help[/bold]\n")
    console.print("[bold]Main menus[/bold]")
    console.print("Use the numbered options shown on each menu. The Main Menu has no Back option because it is the root.")
    console.print()
    console.print("[bold]Inside an interactive operation[/bold]")
    console.print("B / Back   — return to the immediately previous screen")
    console.print("0 / Exit   — exit the framework safely")
    console.print()
    console.print("Invalid input should keep you on the current screen so you can try again.")
    console.print("For JSON inputs, enter a valid JSON object when the operation requests JSON.")
    console.print()
