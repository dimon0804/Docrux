"""Раскладка распознанных строк по полям карточки.

Документ читается как набор строк «Метка: значение». Метки и их варианты
берутся из описания типа, поэтому модуль ничего не знает о конкретных
документах.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from paragraf import textnorm
from paragraf.doctypes import CompositeSpec, DocType, FieldSpec
from paragraf.models import Box, Line

LABEL_THRESHOLD = 82.0


@dataclass
class Found:
    raw: str
    box: Box | None
    confidence: float
    label_line: Line


@dataclass
class _Target:
    label: str
    key: str
    field: FieldSpec | None
    composite: CompositeSpec | None
    primary: bool


def _targets(doc_type: DocType) -> list[_Target]:
    targets = []
    for field in doc_type.fields:
        for index, label in enumerate(field.labels):
            targets.append(_Target(textnorm.match_key(label), field.key, field, None, index == 0))
    for composite in doc_type.composites:
        for index, label in enumerate(composite.labels):
            key = "+".join(composite.keys)
            targets.append(_Target(textnorm.match_key(label), key, None, composite, index == 0))
    return targets


def _split(line: Line) -> tuple[str, str, int] | None:
    """Делит строку на метку и значение по первому двоеточию.

    Возвращает метку, значение и число слов, которые ушли в метку.
    """
    words = line.words or []
    for index, word in enumerate(words):
        if ":" in word.text:
            head, _, tail = word.text.partition(":")
            label = " ".join([*(w.text for w in words[:index]), head])
            value = " ".join([tail, *(w.text for w in words[index + 1 :])]).strip()
            return label, value, index + 1
    if ":" in line.text:
        label, _, value = line.text.partition(":")
        return label, value.strip(), len(label.split())
    return None


def _score(candidate: str, target: _Target) -> float:
    score = fuzz.ratio(candidate, target.label)
    # Короткие варианты меток («Дата», «Номер») годятся только при точном совпадении.
    if not target.primary and len(target.label) <= 6 and score < 100:
        return 0.0
    return score


def _value_box(line: Line, skip_words: int) -> Box | None:
    words = (line.words or [])[skip_words:]
    words = [word for word in words if not textnorm.is_blank(word.text)]
    if not words:
        return None
    box = words[0].box
    for word in words[1:]:
        box = box.union(word.box)
    return box


def _value_confidence(line: Line, skip_words: int) -> float:
    words = (line.words or [])[skip_words:]
    return min((word.confidence for word in words), default=line.confidence)


def locate(doc_type: DocType, lines: list[Line]) -> dict[str, Found]:
    """Находит строки с метками и возвращает сырое значение для каждого ключа."""
    targets = _targets(doc_type)
    candidates: list[tuple[float, int, _Target, str, int]] = []

    for index, line in enumerate(lines):
        split = _split(line)
        if split is not None:
            label, value, used = split
            key = textnorm.match_key(label)
            for target in targets:
                score = _score(key, target)
                if score >= LABEL_THRESHOLD:
                    candidates.append((score, index, target, value, used))
            continue
        # Двоеточие могло потеряться при распознавании: ищем метку в начале строки.
        text_words = line.text.split()
        for target in targets:
            size = len(target.label.split())
            if not target.primary or size > len(text_words):
                continue
            key = textnorm.match_key(" ".join(text_words[:size]))
            score = fuzz.ratio(key, target.label)
            if score >= 92:
                candidates.append((score - 5, index, target, " ".join(text_words[size:]), size))

    found: dict[str, Found] = {}
    used_lines: set[int] = set()
    for _, index, target, value, used in sorted(candidates, key=lambda item: -item[0]):
        if index in used_lines or target.key in found:
            continue
        line = lines[index]
        value, box = _with_continuation(lines, index, value, _value_box(line, used))
        used_lines.add(index)
        found[target.key] = Found(value, box, _value_confidence(line, used), line)
    return found


def _with_continuation(
    lines: list[Line], index: int, value: str, box: Box | None
) -> tuple[str, Box | None]:
    """Добавляет перенос значения на следующую строку, если он есть."""
    line = lines[index]
    if textnorm.is_blank(value):
        # Значение может стоять правее в той же строке как отдельный блок.
        for other in lines[index + 1 : index + 3]:
            same_row = abs((other.box.y + other.box.h / 2) - (line.box.y + line.box.h / 2))
            to_the_right = other.box.x > line.box.x + line.box.w
            filled = ":" not in other.text and not textnorm.is_blank(other.text)
            if same_row < line.box.h * 0.6 and to_the_right and filled:
                return other.text, other.box
        return value, box
    if index + 1 >= len(lines):
        return value, box
    following = lines[index + 1]
    gap = following.box.y - (line.box.y + line.box.h)
    aligned = abs(following.box.x - line.box.x) < 0.03
    wraps = line.box.x + line.box.w > 0.8
    if aligned and wraps and 0 <= gap < line.box.h * 0.9 and ":" not in following.text:
        joined_box = box.union(following.box) if box else following.box
        return f"{value} {following.text}", joined_box
    return value, box


def normalize(spec: FieldSpec, raw: str) -> str | None:
    """Приводит сырое значение к виду карточки. None означает «не найдено»."""
    value = textnorm.strip_placeholder(raw)
    if textnorm.is_blank(value):
        return None
    if spec.type == "date":
        return textnorm.parse_date(value)
    if spec.type == "integer":
        return textnorm.parse_integer(value)
    if spec.type == "code":
        return textnorm.clean_code(value) or None
    if spec.type == "person":
        return textnorm.clean_person(value) or None
    return textnorm.clean_text(value) or None


def split_composite(composite: CompositeSpec, raw: str) -> dict[str, str]:
    """Разбирает составную строку на сырые значения отдельных полей."""
    value = textnorm.strip_placeholder(raw)
    keys = composite.keys
    if composite.kind == "date_range":
        dates = _date_chunks(value)
        return dict(zip(keys, dates, strict=False))
    if composite.kind == "number_and_date":
        dates = _date_chunks(value)
        number = value
        if dates:
            number = value.replace(dates[0], " ")
        number = re.sub(r"\b(от|г|года)\b\.?", " ", number, flags=re.IGNORECASE)
        out = {keys[0]: textnorm.strip_placeholder(number)}
        if dates:
            out[keys[1]] = dates[0]
        return out
    if composite.kind == "group_and_course":
        course = re.search(r"(\d)\s*(?:-?й)?\s*курс|курс\s*(\d)", value, flags=re.IGNORECASE)
        out = {}
        rest = value
        if course:
            out[keys[1]] = course[1] or course[2]
            rest = value.replace(course[0], " ")
        else:
            parts = [part.strip() for part in re.split(r"[,;/]", value) if part.strip()]
            if len(parts) == 2 and parts[1].isdigit():
                out[keys[1]], rest = parts[1], parts[0]
        rest = re.sub(r"\bгруппа\b", " ", rest, flags=re.IGNORECASE)
        out[keys[0]] = textnorm.strip_placeholder(rest.strip(" ,;/"))
        return out
    return {}


_DATE_CHUNK = re.compile(
    r"\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}\s*[./]\s*\d{1,2}\s*[./]\s*\d{2,4}"
    r"|\d{1,2}\s*[\"«»]?\s*[А-Яа-яёЁ]{3,}\.?\s*\d{4}(?:\s*(?:года|г\.?))?"
)


def _date_chunks(value: str) -> list[str]:
    return [match.group(0) for match in _DATE_CHUNK.finditer(value)]
