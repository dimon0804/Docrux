from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from paragraf.bot import logic
from paragraf.bot.logic import ChatStore
from paragraf.models import Analysis, FieldValue, Validation
from paragraf.pipeline import Pipeline
from paragraf.settings import Settings


def _analysis(pipeline: Pipeline, open_dir: Path, name: str) -> Analysis:
    return pipeline.analyze((open_dir / "documents" / f"{name}.pdf").read_bytes()).analysis


def _other(fields: list[FieldValue] | None = None) -> Analysis:
    return Analysis(
        document_type="other",
        document_title="Протокол заседания <кафедры>",
        supported=False,
        type_detected=True,
        ocr_engine="test",
        text="",
        fields=fields or [],
        validation=Validation(status="not_applicable", missing_fields=[], sources=[]),
        width=1,
        height=1,
    )


def test_complete_certificate_report(pipeline: Pipeline, open_dir: Path):
    analysis = _analysis(pipeline, open_dir, "open-001")
    text = logic.format_report(analysis, pipeline.check(analysis))
    assert text.startswith("<b>Справка об обучении</b>\nТип документа определён автоматически.")
    assert "Документ содержит все обязательные сведения" in text
    assert "<i>Источники: п. 3.1, п. 3.2, п. 3.3</i>" in text
    assert "ФИО студента: Александров Артём Игоревич" in text
    assert "Дата выдачи: 1 сентября 2026 года" in text
    assert "Печать вуза: есть" in text
    # Ёлочки остаются как есть: экранируются только служебные символы HTML.
    assert "Учебный университет «Меридиан»" in text


def test_missing_field_report_with_question(pipeline: Pipeline, open_dir: Path):
    analysis = _analysis(pipeline, open_dir, "open-012")
    question = "Кто принимает окончательное решение?"
    answer = pipeline.ask(analysis, question, True)
    text = logic.format_report(analysis, pipeline.check(analysis), question, answer)
    assert text.startswith("<b>Заявление на академический отпуск</b>")
    assert "Не хватает: дата заявления (п. 4.1)" in text
    assert "Дата заявления: <i>не найдено</i>" in text
    assert "<b>Вопрос:</b> Кто принимает окончательное решение?" in text
    assert text.endswith("<i>Источник: п. 1.3</i>")


def test_field_sources_use_labels(pipeline: Pipeline, open_dir: Path):
    analysis = _analysis(pipeline, open_dir, "open-001")
    answer = pipeline.ask(analysis, "Что это за документ?", True)
    text = logic.format_answer("Что это за документ?", answer, analysis)
    assert "поле «ФИО студента»" in text
    assert "field:" not in text
    assert logic.source_label("field:nope", analysis) == "поле «nope»"
    assert logic.format_sources([]) == ""


def test_manual_type_is_reported(pipeline: Pipeline, open_dir: Path):
    data = (open_dir / "documents" / "open-001.pdf").read_bytes()
    analysis = pipeline.analyze(data, "study_certificate").analysis
    text = logic.format_report(analysis, pipeline.check(analysis))
    assert "Тип документа выбран вручную." in text


def test_unsupported_report_is_escaped(pipeline: Pipeline):
    fields = [
        FieldValue(key="g1", label="Дата <b>", type="text", value="1 & 2", found=True),
    ]
    analysis = _other(fields)
    text = logic.format_report(analysis, pipeline.check(analysis))
    assert "<b>Этот вид документа я не проверяю</b>" in text
    assert "«Протокол заседания &lt;кафедры&gt;»" in text
    assert "пункт 1.2" in text
    assert "Дата &lt;b&gt;: 1 &amp; 2" in text
    assert "<i>Источник: п. 1.2</i>" in text


def test_long_card_fits_one_message(pipeline: Pipeline):
    fields = [
        FieldValue(key=f"g{i}", label=f"Строка {i}", type="text", value="x" * 400, found=True)
        for i in range(30)
    ]
    analysis = _other(fields)
    answer = pipeline.ask(analysis, "Что это за документ?", True)
    text = logic.format_report(analysis, pipeline.check(analysis), "Что это за документ?", answer)
    assert len(text) <= logic.MESSAGE_LIMIT
    assert "…и ещё" in text
    assert "<b>Вопрос:</b>" in text


def test_field_values():
    mark = FieldValue(key="seal", label="Печать", type="mark", value=False, found=False)
    hand = FieldValue(
        key="a", label="A", type="text", value="не найдено", found=False, handwritten=True
    )
    date = FieldValue(key="d", label="D", type="date", value="2026-02-03", found=True)
    assert logic.field_value(mark) == "не найдена"
    assert logic.field_value(hand).startswith("заполнено от руки")
    assert logic.field_value(date) == "3 февраля 2026 года"


def test_suggestions(pipeline: Pipeline, open_dir: Path):
    analysis = _analysis(pipeline, open_dir, "open-012")
    options = logic.suggestions(analysis)
    assert options[:3] == [
        "Что это за документ?",
        "Чего не хватает?",
        "Кто принимает окончательное решение?",
    ]
    assert options[3] == "Что указано в поле «Дата начала отпуска»?"
    assert "Какие типы документов поддерживаются?" in logic.suggestions(_other())


@pytest.mark.parametrize(
    ("size", "mime", "name", "ok"),
    [
        (1000, "image/jpeg", None, True),
        (1000, "application/pdf", "scan.pdf", True),
        (1000, "application/octet-stream", "SCAN.PNG", True),
        (1000, "application/msword", "letter.doc", False),
        (None, None, "doc.pdf", True),
        (15 * 1024 * 1024, "image/png", None, True),
        (15 * 1024 * 1024 + 1, "image/png", None, False),
    ],
)
def test_check_upload(size, mime, name, ok):
    assert (logic.check_upload(size, 15, mime, name) is None) is ok


def test_clean_question():
    assert logic.clean_question("  Чего\n не   хватает? ") == "Чего не хватает?"
    assert logic.clean_question(None) == ""
    assert len(logic.clean_question("а" * 2000)) == logic.QUESTION_LIMIT


def test_callbacks():
    data = logic.callback_data("t", "12", "academic_leave_application")
    assert logic.parse_callback(data) == logic.Callback("t", "12", "academic_leave_application")
    assert logic.parse_callback(logic.callback_data("m", "3")) == logic.Callback("m", "3", "")
    assert logic.parse_callback("x:1:2") is None
    assert logic.parse_callback("q::1") is None
    assert logic.parse_callback(None) is None
    with pytest.raises(ValueError):
        logic.callback_data("t", "1", "x" * 70)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_store_forgets_after_ttl():
    clock = Clock()
    store = ChatStore(ttl=1800, max_chats=10, clock=clock)
    first = store.put(1, _other(), "file-1")
    clock.now = 1000
    assert store.get(1) is first
    # Вопрос продлевает память: отсчёт идёт от последнего обращения.
    clock.now = 2700
    assert store.get(1) is first
    clock.now = 4600
    assert store.get(1) is None
    assert len(store) == 0


def test_store_tokens_and_cap():
    clock = Clock()
    store = ChatStore(ttl=60, max_chats=2, clock=clock)
    old = store.put(1, _other(), "a")
    new = store.put(1, _other(), "b")
    assert old.token != new.token
    assert store.get(1) is new
    store.put(2, _other(), "c")
    store.get(1)
    store.put(3, _other(), "d")
    # Вытесняется чат, к которому обращались давнее всего.
    assert store.get(2) is None
    assert store.get(1) is not None
    assert store.get(3) is not None
    clock.now = 61
    assert len(store) == 0


def test_help_mentions_rules():
    text = logic.help_text(15, 30)
    for part in ("справка об обучении", "академический отпуск", "справка о практике"):
        assert part in text
    assert "п. 1.3" in text
    assert "не сохраняется" in text
    assert "30 минут" in text


def test_bot_needs_token(settings: Settings):
    app = pytest.importorskip("paragraf.bot.app")
    with pytest.raises(app.BotTokenMissing, match="PARAGRAF_BOT_TOKEN"):
        asyncio.run(app.run(settings.model_copy(update={"bot_token": None})))
    broken = Settings(bot_token="not-a-token")
    with pytest.raises(app.BotTokenMissing) as error:
        asyncio.run(app.run(broken))
    assert "not-a-token" not in str(error.value)


def test_keyboards_fit_telegram_limits(pipeline: Pipeline, open_dir: Path, settings: Settings):
    app = pytest.importorskip("paragraf.bot.app")
    store = ChatStore(ttl=60, max_chats=10)
    state = store.put(1, _analysis(pipeline, open_dir, "open-012"), "file")
    report = app.report_keyboard(state)
    types = app.types_keyboard(pipeline, state)
    buttons = [b for row in report.inline_keyboard + types.inline_keyboard for b in row]
    assert all(len(b.callback_data.encode()) <= 64 for b in buttons)
    assert len(report.inline_keyboard) == 5
    chosen = {
        logic.parse_callback(b.callback_data).arg for row in types.inline_keyboard for b in row
    }
    assert chosen == {
        "study_certificate",
        "academic_leave_application",
        "internship_certificate",
    }
    assert app.build_router(pipeline, settings) is not None


def test_reply_stays_within_limit_when_escaping_inflates_it(pipeline: Pipeline):
    analysis = _other([FieldValue(key="g", label="Строка", type="text", value="ok", found=True)])
    analysis = analysis.model_copy(update={"document_title": "&<" * 60})
    question = "&" * 500
    answer = pipeline.ask(analysis, question, True)
    answer = answer.model_copy(update={"answer": "&<>" * 700})
    text = logic.format_report(analysis, pipeline.check(analysis), question, answer)
    assert len(text) <= logic.MESSAGE_LIMIT


def test_report_lists_remarks(pipeline: Pipeline, open_dir: Path):
    from paragraf.models import Remark

    analysis = pipeline.analyze((open_dir / "documents" / "open-012.pdf").read_bytes()).analysis
    analysis = analysis.model_copy(
        update={
            "remarks": [
                Remark(text="Курс «9» вне обычного диапазона от 1 до 6.", fields=["course"])
            ]
        }
    )
    text = logic.format_report(analysis, pipeline.check(analysis))
    assert "<b>На что обратить внимание</b>\n• Курс «9»" in text
