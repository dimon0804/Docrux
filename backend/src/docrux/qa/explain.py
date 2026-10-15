"""Почему ответ именно такой: короткая цепочка шагов для интерфейса.

Шаги собираются из того же разбора, что и ответ, и ничего к нему не
добавляют: какой вид вопроса распознан, откуда взято значение, какой пункт
Положения процитирован и почему сервис отказался отвечать.
"""

from __future__ import annotations

from docrux.doctypes import DocType
from docrux.models import Analysis, Answer
from docrux.qa.intents import Intent, _vocabulary
from docrux.qa.lexicon import STOPWORDS, stem, tokens


def _labels(analysis: Analysis, keys: list[str]) -> str:
    names = {field.key: field.label for field in analysis.fields}
    return ", ".join(f"«{names.get(key, key)}»" for key in keys)


def _rules(sources: list[str]) -> str:
    numbers = [source[5:] for source in sources if source.startswith("rule:")]
    return ", ".join(numbers)


def explain(
    doc_type: DocType | None,
    analysis: Analysis,
    intent: Intent | None,
    answer: Answer,
    known: frozenset[str],
) -> list[str]:
    """Шаги рассуждения для ответа. ``known`` — основы слов самого Положения."""
    kind = answer.intent
    if kind == "completeness":
        validation = analysis.validation
        steps = ["Вопрос о том, всё ли нужное есть в документе."]
        if doc_type is not None:
            steps.append(f"Сверены обязательные сведения типа «{doc_type.title}».")
        if validation.missing_fields:
            steps.append(f"Не найдено: {_labels(analysis, validation.missing_fields)}.")
        else:
            steps.append("Все обязательные сведения найдены.")
        rules = _rules(answer.sources)
        word = "пункт" if "," not in rules else "пункты"
        steps.append(f"Основание: {word} {rules} Положения.")
        steps.append("Решение остаётся за сотрудником деканата (пункт 1.3).")
        return steps
    if kind == "decision":
        return ["Вопрос о том, кто принимает решение.", "Ответ дан по пункту 1.3 Положения."]
    if kind == "field":
        key = next((s[6:] for s in answer.sources if s.startswith("field:")), None)
        if key is None and intent is not None and intent.field is not None:
            key = intent.field.key
        field = next((f for f in analysis.fields if f.key == key), None)
        label = field.label if field else (key or "")
        steps = [
            f"Поле названо в вопросе: «{intent.quoted}»."
            if intent and intent.quoted
            else f"Слова вопроса совпали с описанием поля «{label}»."
        ]
        if answer.answerable and field is not None:
            where = {
                "label": f"Значение прочитано на снимке после метки «{label}».",
                "text": "Метки на документе нет: значение найдено в тексте документа.",
                "generic": "Значение прочитано из строки «метка: значение» на снимке.",
            }.get(field.origin or "label", "Значение взято из карточки документа.")
            steps.append(where)
            steps.append("Ответ повторяет значение из карточки без изменений.")
        else:
            steps.append("В документе это поле не найдено, поэтому значения нет.")
        return steps
    if kind == "rule":
        return [
            "Вопрос о правилах, а не о содержимом документа.",
            f"По словам вопроса выбран пункт {_rules(answer.sources)} Положения.",
            "Ответ — дословная цитата пункта, без пересказа.",
        ]
    if kind == "about":
        return [
            "Вопрос о самом документе.",
            "Перечислены поля, прочитанные на снимке, и тип документа.",
        ]
    # Отказ: показываем, каких слов вопроса нет в источниках.
    vocabulary = set(known)
    if doc_type is not None:
        vocabulary |= _vocabulary(doc_type)
    foreign = []
    for word in tokens(answer.question):
        if word in STOPWORDS or word.isdigit() or len(word) < 4:
            continue
        if stem(word) not in vocabulary and word not in foreign:
            foreign.append(word)
    steps = []
    if foreign:
        shown = ", ".join(f"«{word}»" for word in foreign[:3])
        steps.append(f"Слов {shown} нет ни в документе, ни в Положении.")
    else:
        steps.append("Вопрос не относится ни к полям документа, ни к пунктам Положения.")
    steps.append("Отвечать по догадке сервис не будет, поэтому честно говорит, что ответа нет.")
    return steps
