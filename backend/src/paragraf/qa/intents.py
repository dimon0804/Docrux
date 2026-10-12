"""Определение того, о чём спрашивает студент.

Вопрос относится к одному из видов:

* ``completeness`` — всё ли есть в документе;
* ``decision`` — кто принимает окончательное решение;
* ``field`` — значение конкретного поля карточки;
* ``unknown`` — в документе и Положении ответа нет.

Сначала проверяются явные формулировки, затем вопрос сопоставляется с
метками полей и примерами вопросов из описания типа документа.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from paragraf import textnorm
from paragraf.doctypes import DocType, FieldSpec
from paragraf.qa.lexicon import stems

_QUOTED = re.compile(r"[«\"“„]([^«»\"“”„]{2,60})[»\"”]")

_DECISION = re.compile(
    r"кто\b.*\b(принима|прим[еу]т|реша|утвержда|одобр|подтвержда)"
    r"|(окончательн|итогов)\w*\s+решени"
    r"|за\s+кем\s+(последнее\s+слово|решение)"
    r"|кем\s+принима",
)

_COMPLETENESS = re.compile(
    r"все\s+(ли\s+)?(обязательн|необходим|нужн)"
    r"|обязательн\w+\s+(сведен|пол|данн|реквизит)"
    r"|комплект"
    r"|в\s+порядке"
    r"|(чего|что|каких|какие)\b.{0,30}\bне\s+хвата"
    r"|не\s+хватает"
    r"|\bхватит\b|\bхватает\s+ли"
    r"|достаточно\s+ли|\bдостаточн\w+\s+для"
    r"|подходит\s+ли|\bподойд[её]т"
    r"|прим[уе]т\s+ли|примут\b"
    r"|(правильно|верно|корректно|полностью)\s+(ли\s+)?(заполнен|оформлен|составлен)"
    r"|все\s+ли\s+(заполнен|указан|на\s+месте|есть|в\s+порядке)"
    r"|провер(ь|ьте|ить)\b"
    r"|что\s+(нужно\s+)?(исправить|дозаполнить|добавить|дописать)"
    r"|соответству\w+\s+(ли\s+)?(положени|требовани|правил)"
    r"|(каких|какие)\s+(пол|сведен|данн)\w*\s+(нет|отсутств|пропущен)"
    r"|чего\s+(нет|недоста)"
    r"|что\s+(не\s+так|пропущено|отсутствует)",
)


@dataclass
class Intent:
    kind: str
    field: FieldSpec | None = None
    score: float = 0.0
    quoted: str | None = None


def _clean(question: str) -> str:
    return re.sub(r"\s+", " ", question.casefold().replace("ё", "е")).strip()


def _match_quoted(doc_type: DocType, quoted: str) -> FieldSpec | None:
    wanted = textnorm.match_key(quoted)
    best: tuple[float, FieldSpec] | None = None
    for field in doc_type.fields:
        for index, label in enumerate(field.labels):
            score = fuzz.ratio(wanted, textnorm.match_key(label))
            if index and score < 100:
                continue
            if score >= 85 and (best is None or score > best[0]):
                best = (score, field)
    return best[1] if best else None


# Слова, которые допустимы в любом вопросе о документе и не меняют его темы.
_GENERIC = frozenset(
    stems(
        "документ справка заявление бумага студент студентка учащийся выдан выдали указан "
        "написан записан стоит значится сведения данные информация какой именно точно"
    )
)


def _phrases(field: FieldSpec) -> list[str]:
    """Фразы, по которым поле узнаётся в вопросе.

    Варианты меток из одного слова («Номер», «Дата», «Студент») сюда не входят:
    они нужны для чтения документа, а в вопросе слишком многозначны.
    """
    aliases = [alias for alias in field.aliases if len(set(stems(alias))) >= 2]
    return [field.label, *aliases, *field.ask]


def _vocabulary(doc_type: DocType) -> frozenset[str]:
    words: set[str] = set(_GENERIC)
    words.update(stems(doc_type.title))
    for field in doc_type.fields:
        for phrase in [*field.labels, *field.ask]:
            words.update(stems(phrase))
    return frozenset(words)


def _match_field(doc_type: DocType, question: str) -> tuple[FieldSpec, float] | None:
    """Сопоставляет вопрос с полем по меткам и примерам вопросов.

    Фраза считается найденной, если все её значимые слова есть в вопросе.
    Побеждает самая длинная найденная фраза: «дата окончания практики» важнее,
    чем просто «дата». Если в вопросе есть слова, которых нет ни в одном
    описании полей («стипендия», «телефон»), это вопрос о чём-то другом, и
    поле не подбирается.
    """
    asked = set(stems(question))
    if not asked:
        return None
    foreign = asked - _vocabulary(doc_type)
    ranked: list[tuple[float, int, FieldSpec]] = []
    for order, field in enumerate(doc_type.fields):
        best = 0.0
        for phrase in _phrases(field):
            wanted = set(stems(phrase))
            if not wanted or not wanted <= asked:
                continue
            # Чем короче фраза, тем строже требование к остальным словам вопроса.
            if len(foreign) > (1 if len(wanted) >= 2 else 0):
                continue
            extra = len(asked - wanted)
            best = max(best, len(wanted) - 0.15 * extra)
        if best > 0:
            ranked.append((best, -order, field))
    if not ranked:
        return None
    ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))
    top = ranked[0]
    if len(ranked) > 1 and abs(ranked[1][0] - top[0]) < 1e-9:
        # Два поля подходят одинаково хорошо: вопрос неоднозначен.
        return None
    return top[2], top[0]


def detect(doc_type: DocType, question: str) -> Intent:
    text = _clean(question)

    quoted = _QUOTED.search(question)
    if quoted and re.search(r"\bпол[еяю]\b|значени", text):
        field = _match_quoted(doc_type, quoted[1])
        if field is not None:
            return Intent("field", field, 1.0, quoted[1])
        return Intent("unknown", quoted=quoted[1])

    if _DECISION.search(text):
        return Intent("decision", score=1.0)
    if _COMPLETENESS.search(text):
        return Intent("completeness", score=1.0)

    if quoted:
        field = _match_quoted(doc_type, quoted[1])
        if field is not None:
            return Intent("field", field, 1.0, quoted[1])

    matched = _match_field(doc_type, question)
    if matched is not None:
        return Intent("field", matched[0], matched[1])
    return Intent("unknown")
