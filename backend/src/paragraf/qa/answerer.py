"""Формирование ответа на вопрос студента.

Ответ собирается только из двух источников: карточки документа и пунктов
Положения. Если ни там, ни там ответа нет, сервис так и говорит.
"""

from __future__ import annotations

from datetime import date

from paragraf.doctypes import DocType
from paragraf.models import Analysis, Answer
from paragraf.qa.intents import detect
from paragraf.rules.kb import RuleBook
from paragraf.textnorm import NOT_FOUND

DECISION_RULE = "1.3"
DECISION_VALUE = "сотрудник деканата"
NO_ANSWER = (
    "В документе и в Положении нет информации для ответа на этот вопрос. Обратитесь в деканат."
)
COMPLETENESS_QUESTION = "Содержит ли документ все обязательные сведения?"

_MONTHS = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]


def _rule_list(rules: list[str]) -> str:
    return ", ".join(rules)


def _points_word(rules: list[str]) -> str:
    return "пункту" if len(rules) == 1 else "пунктам"


def human_date(iso: str) -> str:
    try:
        parsed = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{parsed.day} {_MONTHS[parsed.month - 1]} {parsed.year} года"


class Answerer:
    def __init__(self, rulebook: RuleBook):
        self.rulebook = rulebook

    def answer(self, doc_type: DocType, analysis: Analysis, question: str) -> Answer:
        intent = detect(doc_type, question)
        if intent.kind == "completeness":
            return self.completeness(doc_type, analysis, question)
        if intent.kind == "decision" and DECISION_RULE in self.rulebook:
            return Answer(
                question=question,
                intent="decision",
                answerable=True,
                value=DECISION_VALUE,
                answer=(
                    "Окончательное решение принимает сотрудник деканата. Сервис делает только "
                    f"предварительную проверку (пункт {DECISION_RULE} Положения)."
                ),
                sources=[f"rule:{DECISION_RULE}"],
            )
        if intent.kind == "field" and intent.field is not None:
            return self._field(analysis, question, intent.field.key)
        return Answer(
            question=question,
            intent="unknown",
            answerable=False,
            value=None,
            answer=NO_ANSWER,
            sources=[],
        )

    def completeness(self, doc_type: DocType, analysis: Analysis, question: str = "") -> Answer:
        validation = analysis.validation
        rules = [source.removeprefix("rule:") for source in validation.sources]
        if validation.status == "document_ok":
            text = (
                f"Документ содержит все обязательные сведения по пунктам {_rule_list(rules)} "
                "Положения. Окончательное решение примет сотрудник деканата."
                if len(rules) > 1
                else f"Документ содержит все обязательные сведения по пункту {_rule_list(rules)} "
                "Положения. Окончательное решение примет сотрудник деканата."
            )
        else:
            parts = []
            for key in validation.missing_fields:
                spec = doc_type.field(key)
                parts.append(f"{_lower_first(spec.label)} (п. {spec.rule})")
            text = (
                f"Не хватает: {', '.join(parts)}. Эти сведения обязательны по "
                f"{_points_word(rules)} {_rule_list(rules)} Положения. Остальные поля прочитаны. "
                "Окончательное решение примет сотрудник деканата."
            )
        return Answer(
            question=question or COMPLETENESS_QUESTION,
            intent="completeness",
            answerable=True,
            value=validation.status,
            answer=text,
            sources=list(validation.sources),
            highlight=list(validation.missing_fields),
        )

    def _field(self, analysis: Analysis, question: str, key: str) -> Answer:
        field = analysis.field(key)
        source = f"field:{key}"
        if field.type == "mark":
            present = bool(field.value)
            text = (
                f"{field.label}: отметка на документе есть."
                if present
                else f"{field.label}: отметка на документе не найдена. Она обязательна по "
                f"пункту {field.rule} Положения."
            )
            return Answer(
                question=question,
                intent="field",
                answerable=True,
                value="есть" if present else "нет",
                answer=text,
                sources=[source],
                highlight=[key],
            )
        if not field.found or field.value == NOT_FOUND:
            return Answer(
                question=question,
                intent="field",
                answerable=False,
                value=None,
                answer=(
                    f"Поле «{field.label}» в документе не заполнено, поэтому ответить нельзя. "
                    f"Оно обязательно по пункту {field.rule} Положения."
                ),
                sources=[],
                highlight=[key],
            )
        value = str(field.value)
        shown = f"{human_date(value)} ({value})" if field.type == "date" else value
        return Answer(
            question=question,
            intent="field",
            answerable=True,
            value=value,
            answer=f"{field.label}: {shown}.",
            sources=[source],
            highlight=[key],
        )


def _lower_first(text: str) -> str:
    """«Дата выдачи» -> «дата выдачи», но «ФИО студента» остаётся как есть."""
    first = text.split(" ", 1)[0]
    return text if first.isupper() and len(first) > 1 else text[:1].lower() + text[1:]
