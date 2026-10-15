"""Настройки сервиса. Всё меняется переменными окружения с префиксом DOCRUX_."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_config_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config"
        if (candidate / "doc_types").is_dir():
            return candidate
    return Path("config")


def _default_open_set_dir() -> Path | None:
    """Открытый набор организаторов: в образе /app/data/open, при разработке data/open."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "open"
        if (candidate / "documents.json").is_file():
            return candidate
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCRUX_", env_file=".env", extra="ignore")

    config_dir: Path = _default_config_dir()
    open_set_dir: Path | None = _default_open_set_dir()
    """Открытый набор для самопроверки из интерфейса. Если не найден, кнопка скрыта."""
    ocr_lang: str = "rus"
    ocr_psm: int = 6
    tessdata: str | None = None

    pdf_text_layer: Literal["ignore", "prefer"] = "ignore"
    """ignore: PDF распознаётся как картинка. prefer: берётся текстовый слой, если он есть."""

    speech_model: Path | None = None
    """Папка с моделью Vosk для вопросов голосом. Если не задана или пуста, голос выключен."""

    handwriting_model: str | None = None
    """Папка с моделью рукописного текста. Если не задана, почерк не читается."""

    max_upload_mb: int = 15
    rate_limit_per_minute: int = 30
    trust_proxy: bool = False
    """Верить заголовку X-Forwarded-For. Включается только за своим обратным прокси."""
    cors_origins: list[str] = []
    environment: Literal["dev", "prod"] = "prod"

    bot_token: SecretStr | None = None
    """Токен Telegram-бота от @BotFather. Нужен только команде docrux bot."""
    bot_memory_minutes: int = 30
    """Сколько бот помнит карточку последнего документа чата для вопросов."""
    bot_max_chats: int = 1000
    bot_files_per_minute: int = 5
    bot_messages_per_minute: int = 20
    bot_web_app_url: str | None = None
    """Адрес сайта по HTTPS. Если задан, бот открывает сервис прямо в Telegram (Mini App)."""
    bot_proxy: SecretStr | None = None
    """Прокси для запросов к api.telegram.org, если сервер не достаёт до Telegram напрямую.
    Вид: http://логин:пароль@адрес:порт или socks5://... В нём пароль, поэтому SecretStr."""

    @property
    def doc_types_dir(self) -> Path:
        return self.config_dir / "doc_types"

    @property
    def rules_path(self) -> Path:
        return self.config_dir / "rules.md"

    @property
    def hints_path(self) -> Path:
        return self.config_dir / "rules_hints.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()
