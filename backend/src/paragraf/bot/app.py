"""Обработчики Telegram и запуск бота.

Здесь только связка с aiogram: тексты, проверки и память чатов живут в logic.py.
"""

from __future__ import annotations

import asyncio
import logging
from html import escape

import structlog
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.token import TokenValidationError

from paragraf.api.security import RateLimiter
from paragraf.bot import logic
from paragraf.bot.logic import ChatState, ChatStore
from paragraf.imaging.loader import UnsupportedFile
from paragraf.pipeline import Pipeline, TypeNotDetected
from paragraf.settings import Settings, get_settings

log = structlog.get_logger()

MAX_PARALLEL_OCR = 2
"""Как у API: распознавание грузит процессор, больше двух разборов сразу не запускаем."""


class BotTokenMissing(RuntimeError):
    """Токен не задан или явно неверный: запускать бота не с чем."""


def report_keyboard(state: ChatState) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=text, callback_data=logic.callback_data("q", state.token, str(i))
            )
        ]
        for i, text in enumerate(logic.suggestions(state.analysis))
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="Выбрать тип документа вручную",
                callback_data=logic.callback_data("m", state.token),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def types_keyboard(pipeline: Pipeline, state: ChatState) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=doc_type.title,
                callback_data=logic.callback_data("t", state.token, doc_type.id),
            )
        ]
        for doc_type in pipeline.registry
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_router(pipeline: Pipeline, settings: Settings) -> Router:
    router = Router(name="paragraf")
    # Только личные чаты: в группах бот не нужен, а лимиты там проще обойти.
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")
    store = ChatStore(settings.bot_memory_minutes * 60, settings.bot_max_chats)
    files = RateLimiter(settings.bot_files_per_minute, max_clients=settings.bot_max_chats)
    messages = RateLimiter(settings.bot_messages_per_minute, max_clients=settings.bot_max_chats)
    slots = asyncio.Semaphore(MAX_PARALLEL_OCR)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    help_text = logic.help_text(settings.max_upload_mb, settings.bot_memory_minutes)

    def allowed(limiter: RateLimiter, user_id: int) -> tuple[bool, str]:
        # Считаем по человеку, а не по чату: иначе лимит обходится созданием новых групп.
        ok, retry_after = limiter.allow(str(user_id))
        return ok, logic.TOO_OFTEN.format(seconds=retry_after)

    async def process(
        bot: Bot, chat_id: int, file_id: str, type_id: str | None, question: str
    ) -> None:
        async with ChatActionSender.typing(chat_id=chat_id, bot=bot):
            try:
                # Файл скачиваем, только когда подошла очередь: ожидающие не держат его в памяти.
                async with slots:
                    buffer = await bot.download(file_id)
                    data = buffer.read() if buffer else b""
                    if len(data) > max_bytes:
                        raise UnsupportedFile(f"Файл больше {settings.max_upload_mb} МБ.")
                    processed = await asyncio.to_thread(pipeline.analyze, data, type_id)
                analysis = processed.analysis
                check = await asyncio.to_thread(pipeline.check, analysis)
                answer = (
                    await asyncio.to_thread(pipeline.ask, analysis, question, True)
                    if question
                    else None
                )
            except (UnsupportedFile, TypeNotDetected) as exc:
                await bot.send_message(chat_id, escape(str(exc)))
                return
            except TelegramAPIError as exc:
                log.warning("bot_download_failed", error=type(exc).__name__)
                await bot.send_message(chat_id, logic.FAILED)
                return
            except Exception as exc:
                log.error("bot_analyze_failed", error=type(exc).__name__)
                await bot.send_message(chat_id, logic.FAILED)
                return

        state = store.put(chat_id, analysis, file_id)
        try:
            await bot.send_message(
                chat_id,
                logic.format_report(analysis, check, question or None, answer),
                reply_markup=report_keyboard(state),
            )
        except TelegramAPIError as exc:
            log.warning("bot_reply_failed", error=type(exc).__name__)
            await bot.send_message(chat_id, logic.FAILED)
            return
        log.info(
            "bot_document_analyzed",
            document_type=analysis.document_type,
            status=analysis.validation.status,
            kind=analysis.quality.get("file_kind"),
        )

    async def reply(bot: Bot, chat_id: int, state: ChatState, question: str) -> None:
        answer = await asyncio.to_thread(pipeline.ask, state.analysis, question, True)
        await bot.send_message(
            chat_id,
            logic.format_answer(question, answer, state.analysis),
            reply_markup=report_keyboard(state),
        )

    @router.message(CommandStart())
    @router.message(Command("help"))
    async def on_help(message: Message) -> None:
        site = logic.web_app_url(settings.bot_web_app_url)
        markup = (
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Открыть сервис", web_app=WebAppInfo(url=site))]
                ]
            )
            if site
            else None
        )
        await message.answer(escape(help_text), reply_markup=markup)

    @router.message(F.photo | F.document)
    async def on_file(message: Message, bot: Bot) -> None:
        chat_id = message.chat.id
        if message.photo:
            # Telegram присылает несколько размеров снимка, последний самый крупный.
            item = message.photo[-1]
            problem = logic.check_upload(item.file_size, settings.max_upload_mb)
            file_id = item.file_id
        else:
            document = message.document
            assert document is not None
            problem = logic.check_upload(
                document.file_size, settings.max_upload_mb, document.mime_type, document.file_name
            )
            file_id = document.file_id
        if problem:
            await message.answer(escape(problem))
            return
        ok, why = allowed(files, message.from_user.id if message.from_user else chat_id)
        if not ok:
            await message.answer(escape(why))
            return
        await process(bot, chat_id, file_id, None, logic.clean_question(message.caption))

    @router.message(F.text)
    async def on_text(message: Message, bot: Bot) -> None:
        chat_id = message.chat.id
        text = message.text or ""
        if text.startswith("/"):
            await message.answer(escape(help_text))
            return
        state = store.get(chat_id)
        if state is None:
            await message.answer(logic.NO_DOCUMENT)
            return
        question = logic.clean_question(text)
        if not question:
            return
        ok, why = allowed(messages, message.from_user.id if message.from_user else chat_id)
        if not ok:
            await message.answer(escape(why))
            return
        async with ChatActionSender.typing(chat_id=chat_id, bot=bot):
            await reply(bot, chat_id, state, question)

    @router.message()
    async def on_other(message: Message) -> None:
        await message.answer(logic.NOT_A_FILE)

    @router.callback_query()
    async def on_button(query: CallbackQuery, bot: Bot) -> None:
        pressed = logic.parse_callback(query.data)
        chat_id = query.message.chat.id if query.message else None
        state = store.get(chat_id) if chat_id is not None else None
        if pressed is None or chat_id is None or state is None or pressed.token != state.token:
            await query.answer(logic.STALE_BUTTON, show_alert=True)
            return

        if pressed.kind == "q":
            options = logic.suggestions(state.analysis)
            index = int(pressed.arg) if pressed.arg.isdigit() else -1
            if not 0 <= index < len(options):
                await query.answer(logic.STALE_BUTTON, show_alert=True)
                return
            ok, why = allowed(messages, query.from_user.id)
            await query.answer(None if ok else why, show_alert=not ok)
            if ok:
                async with ChatActionSender.typing(chat_id=chat_id, bot=bot):
                    await reply(bot, chat_id, state, options[index])
            return

        if pressed.kind == "m":
            await query.answer()
            await bot.send_message(
                chat_id, logic.CHOOSE_TYPE, reply_markup=types_keyboard(pipeline, state)
            )
            return

        if pressed.arg not in pipeline.registry:
            await query.answer(logic.STALE_BUTTON, show_alert=True)
            return
        ok, why = allowed(files, query.from_user.id)
        await query.answer("Разбираю заново…" if ok else why, show_alert=not ok)
        if ok:
            await process(bot, chat_id, state.file_id, pressed.arg, "")

    return router


async def run(settings: Settings) -> None:
    token = settings.bot_token.get_secret_value().strip() if settings.bot_token else ""
    if not token:
        raise BotTokenMissing(
            "Не задан токен бота. Получите его у @BotFather и передайте "
            "в переменной окружения PARAGRAF_BOT_TOKEN."
        )
    try:
        bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    except TokenValidationError:
        # Сам токен в сообщение не попадает, чтобы не оказаться в логах.
        raise BotTokenMissing(
            "Токен бота не похож на настоящий. Проверьте PARAGRAF_BOT_TOKEN."
        ) from None

    pipeline = await asyncio.to_thread(Pipeline.default, settings)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(pipeline, settings))
    site = logic.web_app_url(settings.bot_web_app_url)
    if site:
        # Кнопка меню рядом с полем ввода открывает сайт внутри Telegram.
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="Параграф", web_app=WebAppInfo(url=site))
            )
        except TelegramAPIError as exc:
            log.warning("bot_menu_button_failed", error=type(exc).__name__)
    log.info("bot_started")
    try:
        await dispatcher.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await bot.session.close()


def main(settings: Settings | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(run(settings or get_settings()))
