"""Module containing editor functionality for the Enterprise Agent Framework."""

import os, shutil, subprocess, sys
from pathlib import Path
from src.config import EDITOR
def open_in_editor(path: Path) -> bool:
    """Execute the open in editor operation."""
    path = path.resolve()
    candidates = [EDITOR] if EDITOR != "auto" else ["code", "cursor", "windsurf"]
    for command in candidates:
        executable = shutil.which(command)
        if executable:
            try: subprocess.Popen([executable, str(path)]); return True
            except OSError: pass
    try:
        if sys.platform.startswith("win"): os.startfile(str(path))
        elif sys.platform == "darwin": subprocess.Popen(["open", str(path)])
        else:
            opener = shutil.which("xdg-open")
            if not opener: return False
            subprocess.Popen([opener, str(path)])
        return True
    except OSError: return False
