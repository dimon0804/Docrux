"""Проверка ответов языковой модели: принимается только то, что подтверждено цитатой."""

from __future__ import annotations

import pytest

from paragraf.models import Analysis
from paragraf.pipeline import Pipeline
from paragraf.qa.answerer import Answerer
from paragraf.qa.llm import Grounded, LocalLLM
from paragraf.rules.kb import RuleBook


@pytest.fixture(scope="module")
def doc(pipeline: Pipeline, open_dir) -> Analysis:
    return pipeline.analyze((open_dir / "documents" / "open-012.pdf").read_bytes()).analysis


@pytest.fixture(scope="module")
def llm(rulebook: RuleBook) -> LocalLLM:
    return LocalLLM("http://127.0.0.1:9", rulebook, timeout=0.2)


def reply(**fields) -> dict:
    base = {"answerable": True, "source": "rules", "rule": "", "quote": "", "answer": "Ответ."}
    return {**base, **fields}


def test_quote_from_the_named_rule_is_accepted(llm: LocalLLM, doc: Analysis):
    grounded = llm._verify(
        reply(rule="4.4", quote="максимальная длительность отпуска", answer="Не установлена."),
        doc,
        "",
    )
    assert grounded is not None and grounded.sources == ["rule:4.4"]


def test_wrong_rule_number_is_corrected_by_the_quote(llm: LocalLLM, doc: Analysis):
    grounded = llm._verify(
        reply(rule="9.9", quote="Печать вуза и подпись сотрудника деканата"), doc, ""
    )
    assert grounded is not None and grounded.sources == ["rule:4.3"]


@pytest.mark.parametrize(
    "bad",
    [
        reply(rule="4.4", quote="стипендия составляет 5000 рублей в месяц"),
        reply(rule="4.4", quote="отпуск"),
        reply(rule="", quote="деканат работает с девяти до шести часов"),
        reply(source="document", quote="телефон деканата 8 800 555 35 35"),
        reply(source="none", quote="что-нибудь достаточно длинное"),
        reply(answerable=False, rule="4.4", quote="максимальная длительность отпуска"),
        reply(rule="4.4", quote="максимальная длительность отпуска", answer=""),
        "не словарь",
    ],
)
def test_unsupported_answers_are_dropped(llm: LocalLLM, doc: Analysis, bad):
    assert llm._verify(bad, doc, "ФИО студента: Захаров Фёдор Дмитриевич") is None


def test_quote_from_a_field_points_to_that_field(llm: LocalLLM, doc: Analysis):
    grounded = llm._verify(
        reply(source="document", quote="по состоянию здоровья", answer="По состоянию здоровья."),
        doc,
        llm._document(doc),
    )
    assert grounded is not None and grounded.sources == ["field:leave_reason"]


def test_unreachable_model_means_no_answer(llm: LocalLLM, doc: Analysis):
    assert llm.available() is False
    assert llm.answer(doc, "На сколько можно взять отпуск?") is None


def test_answerer_falls_back_to_refusal_without_a_model(
    pipeline: Pipeline, rulebook: RuleBook, llm: LocalLLM, doc: Analysis
):
    answerer = Answerer(rulebook, llm)
    doc_type = pipeline.registry.get(doc.document_type)
    answer = answerer.answer(doc_type, doc, "На сколько можно взять отпуск?", assistant=True)
    assert not answer.answerable and answer.sources == []


def test_model_is_asked_only_when_nothing_else_answers(
    pipeline: Pipeline, rulebook: RuleBook, doc: Analysis
):
    class Fake(LocalLLM):
        calls = 0

        def answer(self, analysis, question):
            Fake.calls += 1
            return Grounded(
                "Длительность не установлена.", ["rule:4.4"], "максимальная длительность"
            )

    answerer = Answerer(rulebook, Fake("http://x", rulebook))
    doc_type = pipeline.registry.get(doc.document_type)
    # Обычные вопросы до модели не доходят.
    for question in [
        "В какой группе учится студент?",
        "Кто принимает окончательное решение?",
        "Нужна ли печать на заявлении?",
        "Что это за документ?",
    ]:
        answerer.answer(doc_type, doc, question, assistant=True)
    assert Fake.calls == 0
    # В строгом режиме модель не используется вовсе.
    assert not answerer.answer(doc_type, doc, "На сколько можно взять отпуск?").answerable
    assert Fake.calls == 0
    answer = answerer.answer(doc_type, doc, "На сколько можно взять отпуск?", assistant=True)
    assert Fake.calls == 1 and answer.intent == "model" and answer.sources == ["rule:4.4"]
    assert answer.quote == "максимальная длительность"
