"""Persistenter Scan-Verlauf (JSON, atomar geschrieben)."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

MAX_ENTRIES = 12
MAX_CODE_CHARS = 60000


@dataclass
class HistoryEntry:
    name: str
    language: str
    timestamp: str
    counts: Dict[str, int]
    code: str
    filename: str = "Eingabe"

    @property
    def display_time(self) -> str:
        try:
            return datetime.fromisoformat(self.timestamp).strftime("%H:%M")
        except ValueError:
            return ""

    @classmethod
    def create(
        cls, name: str, language: str, counts: Dict[str, int], code: str, filename: str
    ) -> "HistoryEntry":
        return cls(
            name=name,
            language=language,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            counts={k: int(counts.get(k, 0)) for k in ("cr", "wa", "in")},
            code=code[:MAX_CODE_CHARS],
            filename=filename,
        )

    @classmethod
    def from_dict(cls, raw: object) -> Optional["HistoryEntry"]:
        """Wandelt JSON-Daten in einen Eintrag um. Ungültige Daten ergeben ``None``."""
        if not isinstance(raw, dict):
            return None
        try:
            counts_raw = raw.get("counts") or {}
            return cls(
                name=str(raw["name"]),
                language=str(raw.get("language", "")),
                timestamp=str(raw.get("timestamp", "")),
                counts={k: int(counts_raw.get(k, 0)) for k in ("cr", "wa", "in")},
                code=str(raw.get("code", ""))[:MAX_CODE_CHARS],
                filename=str(raw.get("filename", "Eingabe")),
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            return None


@dataclass
class HistoryStore:
    """Verwaltet bis zu ``max_entries`` Einträge, neueste zuerst."""

    path: Path
    max_entries: int = MAX_ENTRIES
    entries: List[HistoryEntry] = field(default_factory=list)

    def load(self) -> List[HistoryEntry]:
        try:
            raw = json.loads(Path(self.path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = []
        items = raw if isinstance(raw, list) else []
        parsed = (HistoryEntry.from_dict(item) for item in items)
        self.entries = [e for e in parsed if e is not None][: self.max_entries]
        return self.entries

    def add(self, entry: HistoryEntry) -> bool:
        """Fügt einen Eintrag vorn ein. Gibt zurück, ob das Speichern geklappt hat."""
        self.entries.insert(0, entry)
        del self.entries[self.max_entries :]
        return self.save()

    def clear(self) -> None:
        self.entries = []
        self.save()

    def next_input_name(self) -> str:
        return "Eingabe #%d" % (len(self.entries) + 1)

    def save(self) -> bool:
        """Schreibt atomar. Gibt ``False`` zurück, wenn der Speicherort nicht beschreibbar ist."""
        target = Path(self.path)
        tmp_name = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            handle, tmp_name = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
                json.dump([asdict(e) for e in self.entries], fh, ensure_ascii=False, indent=2)
            os.replace(tmp_name, target)
            return True
        except OSError:
            if tmp_name and os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except OSError:
                    pass
            return False
