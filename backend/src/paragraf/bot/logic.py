"""Логика бота без Telegram: проверка файла, тексты ответов и память чатов.

Всё здесь работает с готовыми Analysis и Answer, поэтому проверяется тестами
без сети и без токена.
"""

from __future__ import annotations

import itertools
import time
from collections import OrderedDict
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from html import escape

from paragraf.models import Analysis, Answer, FieldValue
from paragraf.qa.answerer import human_date

MESSAGE_LIMIT = 4096
"""Предел длины сообщения в Telegram."""
VALUE_LIMIT = 200
ANSWER_LIMIT = 2000
"""Рассказ о незнакомом документе перечисляет все найденные строки и бывает очень длинным."""
QUESTION_LIMIT = 500
"""Как у API: длинный текст не вопрос, а попытка нагрузить разбор."""

ALLOWED_MIME = frozenset({"image/jpeg", "image/png", "application/pdf"})
ALLOWED_SUFFIXES = (".jpg", ".jpeg", ".png", ".pdf")

HELP = (
    "Я помогаю подготовить документ для деканата. Пришлите фото или файл документа "
    "(JPG, PNG или PDF до {max_mb} МБ), и я покажу, что в нём прочитал, проверю по "
    "Положению, всё ли на месте, и отвечу на вопросы о нём.\n\n"
    "Проверяю три вида документов:\n"
    "• справка об обучении;\n"
    "• заявление на академический отпуск;\n"
    "• справка о практике.\n\n"
    "Вопрос можно написать в подписи к файлу или отдельным сообщением после него. "
    "Вопросы относятся к последнему присланному документу.\n\n"
    "Фото лучше отправлять файлом: так Telegram не сжимает снимок и текст читается точнее.\n\n"
    "Моя проверка предварительная. Окончательное решение принимает сотрудник деканата "
    "(п. 1.3 Положения).\n\n"
    "Файл разбирается в памяти и нигде не сохраняется. Чтобы отвечать на вопросы, я помню "
    "карточку последнего документа {minutes} минут, потом забываю её."
)
NO_DOCUMENT = (
    "Сначала пришлите документ: фото или файл JPG, PNG или PDF. "
    "После этого можно задавать вопросы о нём."
)
NOT_A_FILE = "Я разбираю только фото и файлы JPG, PNG или PDF."
STALE_BUTTON = "Эта кнопка относится к прошлому документу. Пришлите документ ещё раз."
FAILED = "Не получилось разобрать файл. Попробуйте ещё раз или пришлите снимок получше."
TOO_OFTEN = "Слишком много сообщений подряд. Подождите {seconds} с и попробуйте снова."
CHOOSE_TYPE = "Какой это документ? Я разберу файл ещё раз как документ выбранного типа."


def help_text(max_mb: int, minutes: int) -> str:
    return HELP.format(max_mb=max_mb, minutes=minutes)


def check_upload(
    size: int | None, max_mb: int, mime: str | None = "image/jpeg", name: str | None = None
) -> str | None:
    """Возвращает причину отказа или None, если файл можно скачивать и разбирать.

    Это только первый фильтр по тому, что сообщил Telegram. Настоящий формат
    загрузчик всё равно определяет по содержимому.
    """
    by_mime = (mime or "").lower() in ALLOWED_MIME
    by_name = (name or "").lower().endswith(ALLOWED_SUFFIXES)
    if not (by_mime or by_name):
        return "Поддерживаются только JPG, PNG и PDF."
    if size is not None and size > max_mb * 1024 * 1024:
        return f"Файл больше {max_mb} МБ."
    return None


def clean_question(text: str | None) -> str:
    return " ".join((text or "").split())[:QUESTION_LIMIT]


def source_label(source: str, analysis: Analysis | None = None) -> str:
    """rule:3.1 превращается в «п. 3.1», field:student_name в «поле «ФИО студента»»."""
    kind, _, ref = source.partition(":")
    if kind == "rule":
        return f"п. {ref}"
    if kind == "field":
        label = ref
        if analysis is not None:
            with suppress(KeyError):
                label = analysis.field(ref).label
        return f"поле «{label}»"
    return source


def format_sources(sources: Iterable[str], analysis: Analysis | None = None) -> str:
    labels = list(dict.fromkeys(source_label(item, analysis) for item in sources))
    if not labels:
        return ""
    word = "Источник" if len(labels) == 1 else "Источники"
    return f"<i>{word}: {escape(', '.join(labels))}</i>"


def field_value(field: FieldValue) -> str:
    """Значение поля так, как его показывает карточка на сайте."""
    if isinstance(field.value, bool):
        return "есть" if field.value else "не найдена"
    if not field.found:
        if field.handwritten:
            return "заполнено от руки, прочитать надёжно не удалось"
        return "не найдено"
    value = human_date(field.value) if field.type == "date" else field.value
    return _shorten(value, VALUE_LIMIT)


def _shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def card_lines(analysis: Analysis) -> list[str]:
    lines = []
    for field in analysis.fields:
        value = escape(field_value(field))
        if not field.found:
            value = f"<i>{value}</i>"
        lines.append(f"{escape(field.label)}: {value}")
    return lines


def format_answer(question: str, answer: Answer, analysis: Analysis | None = None) -> str:
    text = _shorten(answer.answer, ANSWER_LIMIT)
    parts = [f"<b>Вопрос:</b> {escape(_shorten(question, QUESTION_LIMIT))}", escape(text)]
    sources = format_sources(answer.sources, analysis)
    if sources:
        parts.append(sources)
    return "\n".join(parts)


def format_report(
    analysis: Analysis,
    check: Answer,
    question: str | None = None,
    answer: Answer | None = None,
) -> str:
    """Ответ на присланный документ: тип, проверка, карточка и ответ на вопрос из подписи."""
    if analysis.supported:
        how = "определён автоматически" if analysis.type_detected else "выбран вручную"
        header = f"<b>{escape(analysis.document_title)}</b>\nТип документа {how}."
        card_title = "<b>Карточка документа</b>"
    else:
        header = (
            "<b>Этот вид документа я не проверяю</b>\n"
            f"Похоже на «{escape(analysis.document_title)}»."
        )
        card_title = "<b>Что удалось прочитать</b>"

    check_block = "<b>Проверка по Положению</b>\n" + escape(check.answer)
    sources = format_sources(check.sources, analysis)
    if sources:
        check_block += "\n" + sources

    tail = ""
    if question and answer is not None:
        tail = "\n\n" + format_answer(question, answer, analysis)

    lines = card_lines(analysis) or ["<i>Пар «название: значение» найти не удалось.</i>"]
    head = f"{header}\n\n{check_block}\n\n{card_title}\n"

    # Карточка документа незнакомого типа бывает длинной: лишние строки обрезаем,
    # чтобы проверка и ответ на вопрос точно поместились в одно сообщение.
    shown = len(lines)
    while True:
        body = "\n".join(lines[:shown])
        if shown < len(lines):
            body += f"\n<i>…и ещё {len(lines) - shown}</i>"
        text = head + body + tail
        if len(text) <= MESSAGE_LIMIT:
            return text
        if shown == 0:
            break
        shown -= 1
    # Даже без карточки не помещается: в названии или ответе много символов, которые
    # при экранировании становятся длиннее. Отправляем короткую сводку без вопроса.
    short = (
        f"<b>{escape(_shorten(analysis.document_title, 80))}</b>\n\n"
        f"{escape(_shorten(check.answer, 500))}\n\n"
        "<i>Подробности не поместились в сообщение. Задайте вопрос отдельно.</i>"
    )
    return short[:MESSAGE_LIMIT]


def suggestions(analysis: Analysis) -> list[str]:
    """Подсказки вопросов, как в окне вопросов на сайте."""
    if not analysis.supported:
        return [
            "Что это за документ?",
            "Какие типы документов поддерживаются?",
            "Кто принимает окончательное решение?",
        ]
    date = next((f for f in analysis.fields if f.type == "date"), None)
    found = [
        "Что это за документ?",
        "Чего не хватает?",
        "Кто принимает окончательное решение?",
    ]
    if date is not None:
        found.append(f"Что указано в поле «{date.label}»?")
    return found


@dataclass(frozen=True)
class Callback:
    """Нажатая кнопка: q — вопрос-подсказка, m — меню типов, t — выбранный тип."""

    kind: str
    token: str
    arg: str = ""


def callback_data(kind: str, token: str, arg: str = "") -> str:
    data = f"{kind}:{token}:{arg}"
    # Telegram принимает не больше 64 байт в данных кнопки.
    if len(data.encode()) > 64:
        raise ValueError("callback data is too long")
    return data


def parse_callback(data: str | None) -> Callback | None:
    if not data:
        return None
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] not in {"q", "m", "t"} or not parts[1]:
        return None
    return Callback(*parts)


@dataclass
class ChatState:
    analysis: Analysis
    file_id: str
    """Идентификатор файла в Telegram: по нему файл скачивается заново для разбора другим типом."""
    token: str
    """Метка документа в кнопках: кнопки старого документа не должны отвечать про новый."""
    expires: float


class ChatStore:
    """Последний документ каждого чата. Живёт только в памяти процесса.

    Запись забывается через ttl секунд после последнего обращения, а при
    переполнении вытесняется чат, к которому обращались давнее всего.
    """

    def __init__(
        self, ttl: float, max_chats: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.ttl = ttl
        self.max_chats = max_chats
        self.clock = clock
        self._items: OrderedDict[int, ChatState] = OrderedDict()
        self._tokens = itertools.count(1)

    def put(self, chat_id: int, analysis: Analysis, file_id: str) -> ChatState:
        self._purge()
        state = ChatState(analysis, file_id, str(next(self._tokens)), self.clock() + self.ttl)
        self._items[chat_id] = state
        self._items.move_to_end(chat_id)
        while len(self._items) > self.max_chats:
            self._items.popitem(last=False)
        return state

    def get(self, chat_id: int) -> ChatState | None:
        state = self._items.get(chat_id)
        if state is None:
            return None
        now = self.clock()
        if now >= state.expires:
            del self._items[chat_id]
            return None
        state.expires = now + self.ttl
        self._items.move_to_end(chat_id)
        return state

    def drop(self, chat_id: int) -> None:
        self._items.pop(chat_id, None)

    def __len__(self) -> int:
        self._purge()
        return len(self._items)

    def _purge(self) -> None:
        now = self.clock()
        for chat_id in [key for key, state in self._items.items() if now >= state.expires]:
            del self._items[chat_id]
