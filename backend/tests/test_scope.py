"""Вопросы на границе документа: чужое поле и цели, которые Положение не оценивает."""

from __future__ import annotations


def _analysis(pipeline, open_dir, name: str):
    return pipeline.analyze((open_dir / "documents" / name).read_bytes()).analysis


def test_field_of_another_document_type_is_not_answered(pipeline, open_dir):
    leave = _analysis(pipeline, open_dir, "open-012.pdf")
    answer = pipeline.ask(leave, "Какова дата выдачи?", True)
    assert answer.answerable is False
    assert answer.sources == []
    assert "поля «дата выдачи» нет" in answer.answer
    assert "справка об обучении" in answer.answer


def test_requirement_question_still_quotes_the_regulations(pipeline, open_dir):
    leave = _analysis(pipeline, open_dir, "open-012.pdf")
    answer = pipeline.ask(leave, "Обязательна ли дата выдачи?", True)
    assert answer.answerable is True
    assert "rule:3.1" in answer.sources


def test_own_field_is_answered_as_before(pipeline, open_dir):
    leave = _analysis(pipeline, open_dir, "open-012.pdf")
    answer = pipeline.ask(leave, "Какая причина отпуска?", True)
    assert answer.answerable is True
    assert answer.sources == ["field:leave_reason"]


def test_completeness_for_a_transfer_mentions_what_the_certificate_cannot_decide(
    pipeline, open_dir
):
    certificate = _analysis(pipeline, open_dir, "open-001.pdf")
    answer = pipeline.ask(certificate, "Хватит ли этой справки для перевода на 2 курс?", True)
    # Метрика сравнивает статус и источники проверки: они остаются прежними.
    assert answer.value == "document_ok"
    assert answer.sources == list(certificate.validation.sources)
    assert "пункт 3.5" in answer.answer
    # Тот же вопрос без слова «курс»: пункт 3.5 нужен и здесь.
    short = pipeline.ask(certificate, "Хватит ли этой справки для перевода?", True)
    assert "пункт 3.5" in short.answer
    assert short.sources == list(certificate.validation.sources)
    plain = pipeline.ask(certificate, "Достаточно ли справки?", True)
    assert "3.5" not in plain.answer
