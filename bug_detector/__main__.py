"""Startpunkt: ``python -m bug_detector``."""

import sys


def run() -> int:
    try:
        from bug_detector.ui.app import main
    except ModuleNotFoundError as exc:
        if (exc.name or "").startswith("PyQt6"):
            sys.stderr.write(
                "PyQt6 ist nicht installiert.\n"
                "  Windows/macOS: pip install -r requirements.txt\n"
                "  Kali Linux:    sudo apt install python3-pyqt6\n"
            )
            return 1
        raise
    return main()


if __name__ == "__main__":
    sys.exit(run())
