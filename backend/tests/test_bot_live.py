"""Бот целиком: настоящие обработчики aiogram против поддельного Telegram Bot API.

Поддельный сервер отвечает на методы Bot API, отдаёт файл документа и
запоминает всё, что бот отправил. Токен настоящим не является, в сеть ничего
не уходит.
"""

from __future__ import annotations

import asyncio
import json

import pytest

aiohttp_web = pytest.importorskip("aiohttp.web")
aiogram = pytest.importorskip("aiogram")

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.client.session.aiohttp import AiohttpSession  # noqa: E402
from aiogram.client.telegram import TelegramAPIServer  # noqa: E402
from aiogram.enums import ParseMode  # noqa: E402
from aiogram.types import Update  # noqa: E402

from paragraf.bot.app import build_router  # noqa: E402

TOKEN = "123456:TEST-token-for-local-check"
STUDENT = {"id": 7, "is_bot": False, "first_name": "Студент"}


def _message(update_id: int, chat_type: str = "private", **extra) -> Update:
    chat_id = 42 if chat_type == "private" else -5
    body = {
        "message_id": update_id,
        "date": 0,
        "chat": {"id": chat_id, "type": chat_type},
        "from": STUDENT,
    }
    body.update(extra)
    return Update.model_validate({"update_id": update_id, "message": body})


def _callback(update_id: int, data: str) -> Update:
    message = {"message_id": 101, "date": 0, "chat": {"id": 42, "type": "private"}, "text": "x"}
    query = {
        "id": f"cb{update_id}",
        "from": STUDENT,
        "chat_instance": "ci",
        "data": data,
        "message": message,
    }
    return Update.model_validate({"update_id": update_id, "callback_query": query})


async def _scenario(pipeline, settings, pdf: bytes) -> tuple[list[dict], list[dict]]:
    sent: list[dict] = []
    answers: list[dict] = []

    async def method(request):
        name = request.match_info["method"]
        data = {key: str(value) for key, value in (await request.post()).items()}
        result: object = True
        if name == "getFile":
            result = {"file_id": data["file_id"], "file_unique_id": "u", "file_path": "doc.pdf"}
        elif name == "sendMessage":
            sent.append(data)
            chat = {"id": int(data["chat_id"]), "type": "private"}
            result = {"message_id": 100 + len(sent), "date": 0, "chat": chat, "text": data["text"]}
        elif name == "answerCallbackQuery":
            answers.append(data)
        return aiohttp_web.json_response({"ok": True, "result": result})

    async def download(request):
        return aiohttp_web.Response(body=pdf, content_type="application/pdf")

    app = aiohttp_web.Application()
    app.router.add_post("/bot{token}/{method}", method)
    app.router.add_get("/file/bot{token}/{path:.*}", download)
    runner = aiohttp_web.AppRunner(app)
    await runner.setup()
    site = aiohttp_web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]

    session = AiohttpSession(api=TelegramAPIServer.from_base(f"http://127.0.0.1:{port}"))
    bot = Bot(TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(pipeline, settings))
    document = {
        "file_id": "F1",
        "file_unique_id": "U1",
        "file_name": "open-012.pdf",
        "mime_type": "application/pdf",
        "file_size": len(pdf),
    }
    try:
        await dispatcher.feed_update(bot, _message(1, text="/start"))
        await dispatcher.feed_update(bot, _message(2, text="Что это за документ?"))
        await dispatcher.feed_update(
            bot, _message(3, caption="Хватит ли заявления для отпуска?", document=document)
        )
        await dispatcher.feed_update(
            bot, _message(4, text="Какой размер стипендии положен студенту?")
        )
        keyboard = json.loads(sent[-1]["reply_markup"])["inline_keyboard"]
        await dispatcher.feed_update(bot, _callback(5, keyboard[0][0]["callback_data"]))
        await dispatcher.feed_update(bot, _callback(6, "q:deadbeef:0"))
        await dispatcher.feed_update(bot, _message(7, chat_type="group", text="/start"))
    finally:
        await bot.session.close()
        await runner.cleanup()
    return sent, answers


def test_bot_handles_a_whole_conversation(pipeline, settings, open_dir):
    pdf = (open_dir / "documents" / "open-012.pdf").read_bytes()
    sent, answers = asyncio.run(_scenario(pipeline, settings, pdf))
    texts = [item["text"] for item in sent]

    assert "Проверяю три вида документов" in texts[0]
    assert texts[1].startswith("Сначала пришлите документ")
    report = texts[2]
    assert "<b>Заявление на академический отпуск</b>" in report
    assert "Не хватает: дата заявления (п. 4.1)" in report
    assert "Дата заявления: <i>не найдено</i>" in report
    assert "<b>Вопрос:</b> Хватит ли заявления для отпуска?" in report
    assert "нет информации для ответа" in texts[3]
    assert texts[4].startswith("<b>Вопрос:</b> Что это за документ?")
    assert answers[-1]["text"].startswith("Эта кнопка относится к прошлому документу")
    # В группе бот молчит: последнее сообщение по-прежнему ответ на кнопку.
    assert len(sent) == 5
