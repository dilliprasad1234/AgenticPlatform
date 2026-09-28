"""CLI access to existing execution/framework log files."""
from pathlib import Path
from src.config import PROJECT_ROOT
from src.cli.ui import console, info, error


def show_history() -> None:
    root = PROJECT_ROOT / "logs" / "executions"
    if not root.exists():
        info("No execution logs found.")
        return
    files = sorted(root.rglob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        info("No execution logs found.")
        return
    console.print("\n[bold]Recent Execution Logs[/bold]\n")
    for i, path in enumerate(files[:50], 1):
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        console.print(f"{i}. {path.relative_to(PROJECT_ROOT)} ({size} bytes)")
    console.print()
