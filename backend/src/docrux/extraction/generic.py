"""Разбор документа, который не относится ни к одному известному типу.

Положение описывает проверку только для своих типов документов. Но студент
может загрузить что угодно: протокол, приказ, договор. В этом случае сервис
не отказывает, а показывает распознанный текст, название документа и все
строки вида «Метка: значение», которые удалось найти.
"""

from __future__ import annotations

import re

from docrux import textnorm
from docrux.models import FieldValue, Line

OTHER_TYPE = "other"
MAX_FIELDS = 24
_TITLE_WORDS = re.compile(
    r"\b(справка|заявление|протокол|приказ|договор|акт|выписка|распоряжение|уведомление|"
    r"характеристика|ходатайство|доверенность|расписка|отчёт|отчет|диплом|свидетельство|"
    r"сертификат|удостоверение|направление|заключение|решение|постановление|служебная записка|"
    r"объяснительная|докладная|анкета|квитанция|счёт|счет|накладная|резюме)\b",
    re.IGNORECASE,
)


def guess_title(lines: list[Line]) -> str:
    """Название документа: строка с привычным словом-заголовком или самая крупная сверху."""
    top = [line for line in lines if line.box.y < 0.45 and len(line.text.strip()) >= 4]
    for line in top:
        text = textnorm.squash(line.text)
        letters = [char for char in text if char.isalpha()]
        mostly_upper = letters and sum(char.isupper() for char in letters) / len(letters) > 0.7
        if _TITLE_WORDS.search(text) and (mostly_upper or len(text) <= 60):
            return _sentence_case(text)
    for line in top:
        match = _TITLE_WORDS.search(line.text)
        if match:
            return _sentence_case(match.group(0))
    if top:
        tallest = max(top, key=lambda line: line.box.h)
        return _sentence_case(textnorm.squash(tallest.text))[:80]
    return "Документ"


def _sentence_case(text: str) -> str:
    text = text.strip(" .:;,-–—")
    if text.isupper():
        text = text.capitalize()
    return text[:1].upper() + text[1:] if text else "Документ"


_INNER_LABEL = re.compile(r"(?<=[.;])\s+(?=[А-ЯЁA-Z][^:.;]{1,58}:)")


def _pairs(lines: list[Line]) -> list[tuple[str, str, Line, bool]]:
    """Пары «метка, значение» по строкам документа.

    В одной строке может начаться вторая пара («… дверей. Постановили:»), а её
    значение уйти на следующую строку. Последний признак в кортеже говорит, что
    пара занимает строку с начала и рамку значения можно взять по словам.
    """
    pairs: list[tuple[str, str, Line, bool]] = []
    skip = False
    for index, line in enumerate(lines):
        if skip:
            skip = False
            continue
        parts = _INNER_LABEL.split(line.text)
        for position, part in enumerate(parts):
            label, separator, value = part.partition(":")
            if not separator:
                continue
            value = value.strip()
            last = position == len(parts) - 1
            if not value and last and index + 1 < len(lines) and ":" not in lines[index + 1].text:
                value = lines[index + 1].text
                skip = True
            pairs.append((label, value, line, len(parts) == 1 and not skip))
    return pairs


def generic_fields(lines: list[Line]) -> list[FieldValue]:
    """Все пары «Метка: значение», найденные в документе."""
    fields: list[FieldValue] = []
    seen: set[str] = set()
    for label, value, line, whole in _pairs(lines):
        label = textnorm.squash(label)
        value = textnorm.strip_placeholder(value)
        key = textnorm.match_key(label)
        if not (2 <= len(label) <= 60) or not re.search(r"[А-Яа-яЁёA-Za-z]{2}", label):
            continue
        if not value or key in seen or re.fullmatch(r"[\d\s.]+", label):
            continue
        seen.add(key)
        words = (line.words or []) if whole else []
        split = next((i for i, word in enumerate(words) if ":" in word.text), None)
        tail = words[split + 1 :] if split is not None else []
        box = None
        for word in tail:
            box = word.box if box is None else box.union(word.box)
        fields.append(
            FieldValue(
                key=f"line_{len(fields) + 1}",
                label=label,
                type="text",
                value=textnorm.clean_text(value),
                found=True,
                raw=value,
                box=box or line.box,
                confidence=round(line.confidence, 3),
                origin="generic",
            )
        )
        if len(fields) >= MAX_FIELDS:
            break
    return fields
