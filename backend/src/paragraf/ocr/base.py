"""Общий интерфейс движков распознавания."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from paragraf.models import Box, Line, OcrResult, Word


class OcrEngine(Protocol):
    name: str

    def recognize(self, gray: np.ndarray) -> OcrResult:
        """Распознаёт текст на подготовленном сером изображении."""
        ...


def group_lines(words: list[Word], engine: str, width: int, height: int) -> OcrResult:
    """Собирает слова в строки по вертикальному перекрытию и сортирует сверху вниз."""
    rows: list[list[Word]] = []
    for word in sorted(words, key=lambda item: (item.box.y + item.box.h / 2, item.box.x)):
        center = word.box.y + word.box.h / 2
        for row in rows:
            top = min(item.box.y for item in row)
            bottom = max(item.box.y + item.box.h for item in row)
            if top <= center <= bottom:
                row.append(word)
                break
        else:
            rows.append([word])

    lines: list[Line] = []
    for row in rows:
        row.sort(key=lambda item: item.box.x)
        for chunk in _split_columns(row):
            box = chunk[0].box
            for word in chunk[1:]:
                box = box.union(word.box)
            lines.append(
                Line(
                    text=" ".join(word.text for word in chunk),
                    box=box,
                    words=chunk,
                    confidence=sum(word.confidence for word in chunk) / len(chunk),
                )
            )
    lines.sort(key=lambda item: (item.box.y + item.box.h / 2, item.box.x))
    return OcrResult(engine=engine, lines=lines, width=width, height=height)


def _split_columns(row: list[Word]) -> list[list[Word]]:
    """Делит строку, если между словами большой пробел: это разные блоки страницы."""
    if len(row) < 2:
        return [row]
    height = sorted(word.box.h for word in row)[len(row) // 2]
    chunks, current = [], [row[0]]
    for previous, word in zip(row, row[1:], strict=False):
        gap = word.box.x - (previous.box.x + previous.box.w)
        if gap > max(0.06, 4.0 * height * 0.7):
            chunks.append(current)
            current = [word]
        else:
            current.append(word)
    chunks.append(current)
    return chunks


def make_box(x: float, y: float, w: float, h: float, width: int, height: int) -> Box:
    return Box(x=x / width, y=y / height, w=w / width, h=h / height)
