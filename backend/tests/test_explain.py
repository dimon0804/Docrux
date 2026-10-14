from __future__ import annotations

import pytest

from paragraf.pipeline import Pipeline


@pytest.fixture(scope="module")
def leave(pipeline: Pipeline, open_dir):
    return pipeline.analyze((open_dir / "documents" / "open-012.pdf").read_bytes()).analysis


def test_completeness_trace_names_what_is_missing(pipeline: Pipeline, leave):
    trace = pipeline.ask(leave, "Хватит ли заявления?", True).trace
    assert "Не найдено: «Дата заявления»." in trace
    assert "Основание: пункт 4.1 Положения." in trace


def test_field_trace_for_an_empty_field_names_it(pipeline: Pipeline, leave):
    trace = pipeline.ask(leave, "Дата заявления?", True).trace
    assert trace[0] == "Слова вопроса совпали с описанием поля «Дата заявления»."
    assert "не найдено" in trace[1]


def test_refusal_trace_names_words_missing_from_the_sources(pipeline: Pipeline, leave):
    trace = pipeline.ask(leave, "Какой размер стипендии положен студенту?", True).trace
    assert "«стипендии»" in trace[0]
    assert "честно" in trace[-1]


def test_rule_trace_says_it_quotes(pipeline: Pipeline, leave):
    trace = pipeline.ask(leave, "На сколько можно уйти в академ?", True).trace
    assert "пункт 4.4" in trace[1]
    assert trace[-1].startswith("Ответ — дословная цитата")
