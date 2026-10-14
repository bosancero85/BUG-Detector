"""Sicheres Einlesen von Quelltext-Dateien."""

from __future__ import annotations

from pathlib import Path
from typing import Union

MAX_FILE_BYTES = 1_000_000  # 1 MB wie in der Vorlage


class FileReadError(Exception):
    """Datei konnte nicht gelesen werden. Die Nachricht ist für Nutzer gedacht."""


def read_source_file(path: Union[str, Path], max_bytes: int = MAX_FILE_BYTES) -> str:
    """Liest eine Textdatei ein.

    Löst ``FileReadError`` aus bei: nicht lesbar, größer als ``max_bytes`` oder Binärdatei.
    """
    file_path = Path(path)
    try:
        size = file_path.stat().st_size
    except OSError as exc:
        raise FileReadError("Datei nicht lesbar: %s" % exc.strerror) from exc
    if size > max_bytes:
        raise FileReadError("Datei größer als %d MB." % (max_bytes // 1_000_000 or 1))
    try:
        data = file_path.read_bytes()
    except OSError as exc:
        raise FileReadError("Datei nicht lesbar: %s" % exc.strerror) from exc
    if b"\x00" in data[:8192]:
        raise FileReadError("Binärdateien werden nicht unterstützt.")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
