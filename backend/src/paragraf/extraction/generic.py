"""Разбор документа, который не относится ни к одному известному типу.

Положение описывает проверку только для своих типов документов. Но студент
может загрузить что угодно: протокол, приказ, договор. В этом случае сервис
не отказывает, а показывает распознанный текст, название документа и все
строки вида «Метка: значение», которые удалось найти.
"""

from __future__ import annotations

import re

from paragraf import textnorm
from paragraf.models import FieldValue, Line

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


def generic_fields(lines: list[Line]) -> list[FieldValue]:
    """Все строки «Метка: значение», найденные в документе."""
    fields: list[FieldValue] = []
    seen: set[str] = set()
    for line in lines:
        label, separator, value = line.text.partition(":")
        if not separator:
            continue
        label = textnorm.squash(label)
        value = textnorm.strip_placeholder(value)
        key = textnorm.match_key(label)
        if not (2 <= len(label) <= 60) or not re.search(r"[А-Яа-яЁёA-Za-z]{2}", label):
            continue
        if not value or key in seen or re.fullmatch(r"[\d\s.]+", label):
            continue
        seen.add(key)
        words = line.words or []
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
