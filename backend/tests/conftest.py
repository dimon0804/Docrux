from __future__ import annotations

from pathlib import Path

import pytest

from docrux.doctypes import DocTypeRegistry
from docrux.pipeline import Pipeline
from docrux.rules.kb import RuleBook
from docrux.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
OPEN = ROOT / "data" / "open"


@pytest.fixture(scope="session")
def settings() -> Settings:
    # Тесты читают текстовый слой PDF, поэтому им не нужен установленный Tesseract.
    return Settings(config_dir=ROOT / "config", pdf_text_layer="prefer", rate_limit_per_minute=1000)


@pytest.fixture(scope="session")
def registry(settings: Settings) -> DocTypeRegistry:
    return DocTypeRegistry.load(settings.doc_types_dir)


@pytest.fixture(scope="session")
def rulebook(settings: Settings) -> RuleBook:
    return RuleBook.load(settings.rules_path)


@pytest.fixture(scope="session")
def pipeline(settings: Settings) -> Pipeline:
    return Pipeline.default(settings)


@pytest.fixture(scope="session")
def open_dir() -> Path:
    return OPEN
