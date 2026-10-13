"""Формирование ответа на вопрос студента.

Ответ собирается только из двух источников: карточки документа и пунктов
Положения. Если ни там, ни там ответа нет, сервис так и говорит.
"""

from __future__ import annotations

import re
from datetime import date

from paragraf.doctypes import DocType
from paragraf.models import Analysis, Answer
from paragraf.qa.intents import COMPLETENESS_PATTERN, DECISION_PATTERN, detect
from paragraf.qa.lexicon import stems
from paragraf.qa.retrieval import RuleIndex
from paragraf.rules.kb import RuleBook
from paragraf.textnorm import NOT_FOUND

DECISION_RULE = "1.3"
SCOPE_RULE = "1.2"
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


_ABOUT = re.compile(
    r"что\s+(это\s+)?за\s+(документ|бумаг|справк|файл)"
    r"|как(ой|ого)\s+(это\s+)?(тип|вид)\w*\s+документ"
    r"|какой\s+(это\s+)?документ|что\s+это\s+(такое|за)|что\s+это\b"
    r"|как\s+называется\s+(этот\s+)?документ"
    r"|тип\s+документа|вид\s+документа"
    r"|о\s+чем\s+(этот\s+)?документ"
    r"|что\s+(тут|здесь|в\s+нем|в\s+документе)\s+(написано|указано|есть)"
    r"|что\s+(написано|указано|содержится)\s+в\s+документе"
    r"|перескажи|кратко\s+о\s+документе|опиши\s+документ|расскажи\s+(про|о)\s+документ"
    r"|что\s+(ты\s+)?(прочитал|распознал|нашел|видишь)"
)


class Answerer:
    """Отвечает на вопрос по карточке документа и Положению.

    В строгом режиме поддерживаются только виды ответов из описания формата
    results.json. В режиме помощника добавляются рассказ о документе, поиск по
    пунктам Положения и работа с документами незнакомых типов.
    """

    def __init__(self, rulebook: RuleBook, hints: dict[str, list[str]] | None = None):
        self.rulebook = rulebook
        self.index = RuleIndex(rulebook, hints)

    def answer(
        self,
        doc_type: DocType | None,
        analysis: Analysis,
        question: str,
        assistant: bool = False,
    ) -> Answer:
        if doc_type is None:
            return self._other(analysis, question)

        intent = detect(doc_type, question)
        if intent.kind == "completeness":
            return self.completeness(doc_type, analysis, question)
        if intent.kind == "decision" and DECISION_RULE in self.rulebook:
            return self._decision(question)
        if intent.kind == "field" and intent.field is not None:
            return self._field(analysis, question, intent.field.key)
        if assistant:
            if _ABOUT.search(_plain(question)):
                return self._about(analysis, question)
            section = doc_type.rules[0].split(".")[0] if doc_type.rules else None
            found = self._rule(question, section)
            if found is not None:
                return found
        return self._nothing(question)

    def _nothing(self, question: str) -> Answer:
        return Answer(
            question=question,
            intent="unknown",
            answerable=False,
            value=None,
            answer=NO_ANSWER,
            sources=[],
        )

    def _decision(self, question: str) -> Answer:
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

    def _rule(self, question: str, section: str | None) -> Answer | None:
        """Ответ цитатой из Положения, если нашёлся подходящий пункт."""
        matches = self.index.search(question, section)
        if not matches:
            return None
        parts = [f"Пункт {match.point.number} Положения: «{match.point.text}»" for match in matches]
        return Answer(
            question=question,
            intent="rule",
            answerable=True,
            value=None,
            answer=" ".join(parts),
            sources=[match.point.source for match in matches],
        )

    def _about(self, analysis: Analysis, question: str) -> Answer:
        """Рассказ о том, что это за документ и что в нём прочитано."""
        filled = [field for field in analysis.fields if field.found and field.type != "mark"]
        marks = [field for field in analysis.fields if field.type == "mark"]
        lines = [f"Это {_lower_first(analysis.document_title)}."]
        if filled:
            listed = "; ".join(f"{_lower_first(field.label)}: {_shown(field)}" for field in filled)
            lines.append(f"В документе указано: {listed}.")
        for field in marks:
            lines.append(f"{field.label}: {'есть' if field.found else 'не найдена'}.")
        if analysis.supported:
            missing = len(analysis.validation.missing_fields)
            lines.append(
                "Все обязательные сведения на месте."
                if missing == 0
                else f"Не хватает обязательных сведений: {missing}."
            )
        return Answer(
            question=question,
            intent="about",
            answerable=True,
            value=None,
            answer=" ".join(lines),
            sources=[f"field:{field.key}" for field in filled][:12]
            or list(analysis.validation.sources),
            highlight=[field.key for field in filled],
        )

    def _other(self, analysis: Analysis, question: str) -> Answer:
        """Документ незнакомого типа: отвечаем по прочитанным строкам и Положению."""
        text = _plain(question)
        if _ABOUT.search(text):
            answer = self._about(analysis, question)
            note = (
                " Такой тип документа Положение не описывает, поэтому проверить комплектность "
                f"сервис не может (пункт {SCOPE_RULE})."
            )
            return answer.model_copy(
                update={"answer": answer.answer + note, "sources": [f"rule:{SCOPE_RULE}"]}
            )
        if DECISION_PATTERN.search(text) and DECISION_RULE in self.rulebook:
            return self._decision(question)
        if COMPLETENESS_PATTERN.search(text):
            return Answer(
                question=question,
                intent="completeness",
                answerable=True,
                value=None,
                answer=(
                    "Проверить этот документ по Положению нельзя. Сервис проверяет справку об "
                    "обучении, заявление на академический отпуск и справку о практике (пункт "
                    f"{SCOPE_RULE}). Загруженный документ определён как "
                    f"«{analysis.document_title}». Если это один из трёх типов, выберите его "
                    "вручную и загрузите файл ещё раз."
                ),
                sources=[f"rule:{SCOPE_RULE}"],
            )
        asked = set(stems(question))
        best = None
        for field in analysis.fields:
            wanted = set(stems(field.label))
            if wanted and wanted <= asked and (best is None or len(wanted) > best[0]):
                best = (len(wanted), field)
        if best is not None:
            field = best[1]
            return Answer(
                question=question,
                intent="field",
                answerable=True,
                value=str(field.value),
                answer=f"{field.label}: {field.value}.",
                sources=[f"field:{field.key}"],
                highlight=[field.key],
            )
        return self._rule(question, None) or self._nothing(question)

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


def _plain(question: str) -> str:
    return re.sub(r"\s+", " ", question.casefold().replace("ё", "е")).strip()


def _shown(field) -> str:
    value = str(field.value)
    return human_date(value) if field.type == "date" else value
