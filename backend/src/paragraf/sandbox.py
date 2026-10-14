"""Песочница для нового типа документа.

Бонус кейса: новый тип добавляется описанием полей в конфиге, без правок кода.
В песочнице это можно показать прямо в браузере: описание типа присылается
вместе с документом и применяется только к этому запросу. Набор типов сервиса
не меняется, на диск ничего не пишется.

Описание приходит от посетителя, поэтому возможности урезаны: образцы фраз и
словари приведения (регулярные выражения) не принимаются, YAML-якоря запрещены,
размер описания и число полей ограничены.
"""

from __future__ import annotations

import re

import yaml
from pydantic import ValidationError

from paragraf.doctypes import DocType
from paragraf.models import Analysis
from paragraf.pipeline import Pipeline, Processed
from paragraf.rules.validate import validate

MAX_CONFIG_CHARS = 8000
MAX_FIELDS = 24
MAX_TEXT = 120
MAX_ALIASES = 12
SANDBOX_PREFIX = "sandbox_"

# Якорь «&name» и ссылка «*name» позволяют раздуть маленький YAML до гигабайт.
_ANCHOR = re.compile(r"(^|[\s\[{,:-])[&*][^\s,\]}]")
_FORBIDDEN = ("patterns", "choices")


class SandboxError(ValueError):
    """Описание типа нельзя применить; текст ошибки показывается посетителю."""


EXAMPLE = """\
# Описание нового типа документа. Такой же файл, положенный в config/doc_types,
# добавляет тип в сервис насовсем. Здесь он действует только на этот запрос.
id: student_council_protocol
title: Протокол студенческого совета
fields:
  - key: meeting_date
    label: Дата проведения
    type: date
    rule: "7.1"
  - key: chairman
    label: Председатель
    type: person
    rule: "7.1"
  - key: secretary
    label: Секретарь
    type: person
    rule: "7.1"
  - key: attendees
    label: Присутствовали
    rule: "7.1"
  - key: agenda
    label: Повестка дня
    aliases: ["Повестка"]
    rule: "7.2"
"""


def parse(text: str) -> DocType:
    """Проверяет описание типа и возвращает его. Ошибки понятны человеку."""
    if len(text) > MAX_CONFIG_CHARS:
        raise SandboxError(f"Описание длиннее {MAX_CONFIG_CHARS} символов.")
    if _ANCHOR.search(text):
        raise SandboxError("Якоря и ссылки YAML (& и *) в песочнице не поддерживаются.")
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" в строке {mark.line + 1}" if mark is not None else ""
        raise SandboxError(f"Не получается прочитать YAML{where}.") from None
    if not isinstance(raw, dict):
        raise SandboxError("Описание должно быть словарём с полями id, title и fields.")
    if "freeform" in raw:
        raise SandboxError("Образцы фраз (freeform) в песочнице не поддерживаются.")
    raw.pop("detect", None)
    fields = raw.get("fields")
    if not isinstance(fields, list) or not fields:
        raise SandboxError("Нужен список fields хотя бы с одним полем.")
    if len(fields) > MAX_FIELDS:
        raise SandboxError(f"Полей больше {MAX_FIELDS}.")
    for item in fields:
        if not isinstance(item, dict):
            raise SandboxError("Каждое поле описывается словарём: key, label, type, rule.")
        for name in _FORBIDDEN:
            if name in item:
                raise SandboxError(f"Ключ {name} в песочнице не поддерживается.")
        texts = [item.get("label"), *(item.get("aliases") or []), *(item.get("ask") or [])]
        if len(item.get("aliases") or []) > MAX_ALIASES or len(item.get("ask") or []) > MAX_ALIASES:
            raise SandboxError(f"У поля больше {MAX_ALIASES} вариантов названия.")
        if any(isinstance(value, str) and len(value) > MAX_TEXT for value in texts):
            raise SandboxError(f"Название поля длиннее {MAX_TEXT} символов.")
    for item in raw.get("composites") or []:
        if not isinstance(item, dict):
            raise SandboxError("Составная метка описывается словарём.")
    try:
        doc_type = DocType.model_validate(raw)
    except ValidationError as exc:
        first = exc.errors()[0]
        place = ".".join(str(part) for part in first["loc"])
        raise SandboxError(f"Ошибка в описании: {place}: {first['msg']}.") from None
    if len(doc_type.title) > MAX_TEXT:
        raise SandboxError(f"Название типа длиннее {MAX_TEXT} символов.")
    # Свой префикс, чтобы песочный тип нельзя было принять за настоящий.
    return doc_type.model_copy(update={"id": SANDBOX_PREFIX + doc_type.id[:40]})


def run(pipeline: Pipeline, data: bytes, doc_type: DocType) -> Processed:
    """Читает документ и заполняет карточку по описанию из песочницы."""
    page, prepared, ocr, breaks = pipeline.read(data)
    quality = dict(prepared.quality)
    quality["file_kind"] = page.kind
    quality["pages"] = page.pages
    fields = pipeline.extract(doc_type, ocr.lines, prepared.color)
    analysis = Analysis(
        document_type=doc_type.id,
        document_title=doc_type.title,
        supported=False,
        type_detected=False,
        ocr_engine=ocr.engine,
        text=ocr.text,
        fields=fields,
        validation=validate(doc_type, fields),
        quality=quality,
        page_breaks=breaks,
        width=prepared.color.shape[1],
        height=prepared.color.shape[0],
    )
    return Processed(analysis=analysis, image=prepared.color)
