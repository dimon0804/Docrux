"""Поиск сведений в документе свободной формы.

Не каждый документ состоит из строк «Метка: значение». Настоящая справка
часто написана сплошным текстом: «Дана Иванову Ивану Ивановичу в том, что он
обучается на 2 курсе очной формы…». Для таких случаев в описании типа
документа у поля можно задать образцы фраз. Модуль ищет их в тексте и
возвращает найденный фрагмент вместе с местом на снимке.

Образцы используются только для полей, у которых на документе нет метки.
Если метка есть, а значение не вписано, поле остаётся пустым.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from docrux.doctypes import DocType, FieldSpec
from docrux.models import Box, Line, Word

# Готовые куски для образцов в YAML: {fio}, {date}, {name}, {code}.
FIO = (
    r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ][а-яё]+\s+"
    r"[А-ЯЁ][а-яё]+(?:вич|вн|ич|чн|шн|кызы|оглы)[а-яё]{0,3}"
)
DATE = (
    r"(?:\d{1,2}\s*[./]\s*\d{1,2}\s*[./]\s*\d{2,4}"
    r"|[«\"]?\d{1,2}[»\"]?\s+[а-яё]{3,9}\s+\d{4}(?:\s*(?:года|г\.?))?)"
)
NAME = r"[«\"“„][^«»\"“”„\n]{2,90}[»\"”]"
CODE = r"[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9/\-]{0,19}"
MACROS = {"fio": FIO, "date": DATE, "name": NAME, "code": CODE}

# Слова, после которых ФИО принадлежит должностному лицу, а не студенту.
ROLE_BEFORE = re.compile(
    r"(декан|ректор|проректор|директор|заведующ\w+|руководител\w+|секретар\w+|"
    r"исполнител\w+|начальник\w*|специалист\w*|методист\w*|куратор\w*)[^.\n]{0,40}$",
    re.IGNORECASE,
)


@dataclass
class FreeHit:
    raw: str
    box: Box | None
    confidence: float


class _Text:
    """Текст документа одной строкой с обратной связью от символа к слову."""

    def __init__(self, lines: list[Line]):
        parts: list[str] = []
        self.spans: list[tuple[int, int, Word]] = []
        position = 0
        for line in lines:
            words = line.words or [Word(text=line.text, box=line.box, confidence=line.confidence)]
            for word in words:
                parts.append(word.text)
                self.spans.append((position, position + len(word.text), word))
                position += len(word.text) + 1
        self.text = " ".join(parts)

    def locate(self, start: int, end: int) -> tuple[Box | None, float]:
        words = [word for begin, finish, word in self.spans if begin < end and finish > start]
        if not words:
            return None, 0.0
        # Значение может переноситься на другую строку: рамку ставим по первой строке.
        first = words[0]
        same_row = [w for w in words if abs(w.box.y - first.box.y) < first.box.h * 0.7]
        box = same_row[0].box
        for word in same_row[1:]:
            box = box.union(word.box)
        return box, min(word.confidence for word in words)


@lru_cache(maxsize=512)
def _compile(pattern: str) -> re.Pattern[str]:
    expanded = pattern
    for name, body in MACROS.items():
        expanded = expanded.replace("{" + name + "}", body)
    return re.compile(expanded)


def find(doc_type: DocType, lines: list[Line], keys: set[str]) -> dict[str, FreeHit]:
    """Ищет значения полей по образцам фраз. Возвращает только найденное."""
    if not keys:
        return {}
    text = _Text(lines)
    found: dict[str, FreeHit] = {}
    for spec in doc_type.fields:
        if spec.key not in keys or spec.is_mark:
            continue
        hit = _by_patterns(spec, text) or _by_type(spec, doc_type, text)
        if hit is not None:
            found[spec.key] = hit
    return found


def _by_patterns(spec: FieldSpec, text: _Text) -> FreeHit | None:
    for pattern in spec.patterns:
        match = _compile(pattern).search(text.text)
        if match is None:
            continue
        group = "value" if "value" in match.groupdict() else 0
        raw = match.group(group)
        if not raw or not raw.strip():
            continue
        box, confidence = text.locate(match.start(group), match.end(group))
        return FreeHit(raw.strip(), box, confidence)
    return None


def _by_type(spec: FieldSpec, doc_type: DocType, text: _Text) -> FreeHit | None:
    """Запасной поиск по виду значения, когда ни один образец не подошёл."""
    if spec.type != "person":
        return None
    # Первое поле с ФИО в описании считается владельцем документа: берём первое
    # ФИО в тексте, которое не стоит после должности.
    people = [field.key for field in doc_type.fields if field.type == "person"]
    if spec.key != people[0]:
        return None
    for match in re.finditer(FIO, text.text):
        before = text.text[max(0, match.start() - 60) : match.start()]
        if ROLE_BEFORE.search(before):
            continue
        box, confidence = text.locate(match.start(), match.end())
        return FreeHit(match.group(0), box, confidence)
    return None
