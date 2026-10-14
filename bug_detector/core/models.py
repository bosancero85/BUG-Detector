"""Datenmodelle für Funde und Schweregrade."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List


class Severity(str, Enum):
    """Schweregrad eines Fundes. Die Werte entsprechen den Kürzeln der Vorlage."""

    CRITICAL = "cr"
    WARNING = "wa"
    INFO = "in"

    @property
    def label(self) -> str:
        return _LABELS[self]

    @property
    def rank(self) -> int:
        """Sortierreihenfolge: kritisch zuerst."""
        return _RANKS[self]


_LABELS = {
    Severity.CRITICAL: "Kritisch",
    Severity.WARNING: "Warnung",
    Severity.INFO: "Info",
}
_RANKS = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}


@dataclass(frozen=True)
class Finding:
    """Ein einzelner Fund in einer bestimmten Zeile."""

    severity: Severity
    title: str
    line: int
    problem: str
    root_cause: str
    fix: str
    rule_id: str = ""


def count_by_severity(findings: Iterable[Finding]) -> Dict[Severity, int]:
    """Zählt Funde je Schweregrad. Alle Schweregrade sind immer enthalten."""
    counts = {sev: 0 for sev in Severity}
    for finding in findings:
        counts[finding.severity] += 1
    return counts


def worst_severity_per_line(findings: List[Finding]) -> Dict[int, Severity]:
    """Pro Zeile der schwerste Schweregrad (für die Markierung im Editor)."""
    marks: Dict[int, Severity] = {}
    for finding in findings:
        current = marks.get(finding.line)
        if current is None or finding.severity.rank < current.rank:
            marks[finding.line] = finding.severity
    return marks
