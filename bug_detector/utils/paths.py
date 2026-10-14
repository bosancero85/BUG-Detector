"""Plattformgerechte Speicherorte (Windows, macOS, Linux/Kali)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from bug_detector import APP_ID

HISTORY_FILENAME = "history.json"


def user_data_dir(platform: str = "", environ=None, home=None) -> Path:
    """Ordner für Nutzerdaten. Parameter sind für Tests austauschbar."""
    platform = platform or sys.platform
    env = os.environ if environ is None else environ
    home_dir = Path(home) if home else Path.home()

    if platform.startswith("win"):
        base = Path(env.get("APPDATA") or home_dir / "AppData" / "Roaming")
    elif platform == "darwin":
        base = home_dir / "Library" / "Application Support"
    else:
        base = Path(env.get("XDG_DATA_HOME") or home_dir / ".local" / "share")
    return base / APP_ID


def history_file(**kwargs) -> Path:
    return user_data_dir(**kwargs) / HISTORY_FILENAME
