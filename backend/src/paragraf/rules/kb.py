"""База знаний: Положение, разобранное на нумерованные пункты."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SECTION = re.compile(r"^##\s+(\d+)\.\s+(.+)$")
_POINT = re.compile(r"^(\d+\.\d+)\.\s+(.+)$")


@dataclass(frozen=True)
class RulePoint:
    number: str
    section: str
    text: str

    @property
    def source(self) -> str:
        return f"rule:{self.number}"


class RuleBook:
    """Пункты Положения с доступом по номеру."""

    def __init__(self, title: str, points: list[RulePoint]):
        self.title = title
        self._points = {point.number: point for point in points}

    @classmethod
    def load(cls, path: Path) -> RuleBook:
        return cls.parse(path.read_text(encoding="utf-8"))

    @classmethod
    def parse(cls, markdown: str) -> RuleBook:
        title = "Положение"
        section = ""
        points: list[RulePoint] = []
        current: list[str] | None = None
        number = ""

        def flush() -> None:
            if current is not None:
                points.append(RulePoint(number, section, " ".join(current).strip()))

        for line in markdown.splitlines():
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                continue
            heading = _SECTION.match(line)
            if heading:
                flush()
                current = None
                section = heading[2].strip()
                continue
            point = _POINT.match(line)
            if point:
                flush()
                number, current = point[1], [point[2]]
            elif current is not None and line:
                current.append(line)
        flush()
        if not points:
            raise ValueError("в Положении не найдено ни одного нумерованного пункта")
        return cls(title, points)

    def get(self, number: str) -> RulePoint:
        return self._points[number]

    def __contains__(self, number: str) -> bool:
        return number in self._points

    def __iter__(self):
        return iter(self._points.values())

    def __len__(self) -> int:
        return len(self._points)
