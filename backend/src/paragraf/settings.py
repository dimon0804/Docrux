"""Настройки сервиса. Всё меняется переменными окружения с префиксом PARAGRAF_."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_config_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config"
        if (candidate / "doc_types").is_dir():
            return candidate
    return Path("config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PARAGRAF_", env_file=".env", extra="ignore")

    config_dir: Path = _default_config_dir()
    ocr_lang: str = "rus"
    ocr_psm: int = 6
    tessdata: str | None = None

    pdf_text_layer: Literal["ignore", "prefer"] = "ignore"
    """ignore: PDF распознаётся как картинка. prefer: берётся текстовый слой, если он есть."""

    handwriting_model: str | None = None
    """Папка с моделью рукописного текста. Если не задана, почерк не читается."""

    llm_url: str | None = None
    """Адрес локального сервера llama.cpp. Если не задан, языковая модель не используется."""

    max_upload_mb: int = 15
    rate_limit_per_minute: int = 30
    trust_proxy: bool = False
    """Верить заголовку X-Forwarded-For. Включается только за своим обратным прокси."""
    cors_origins: list[str] = []
    environment: Literal["dev", "prod"] = "prod"

    @property
    def doc_types_dir(self) -> Path:
        return self.config_dir / "doc_types"

    @property
    def rules_path(self) -> Path:
        return self.config_dir / "rules.md"


@lru_cache
def get_settings() -> Settings:
    return Settings()
