"""Карточка, которую прислал клиент: проверка и приведение значений к виду карточки.

Клиенту не верим: лишние ключи отбрасываются, значения обрезаются и проходят ту
же нормализацию, что и распознанные. Неразборчивое значение считается ненайденным.
"""

from __future__ import annotations

from paragraf import textnorm
from paragraf.api.schemas import CardField
from paragraf.doctypes import DocType, FieldSpec
from paragraf.extraction.fields import normalize
from paragraf.extraction.generic import OTHER_TYPE
from paragraf.models import Analysis, FieldValue, Validation
from paragraf.rules.remarks import find_remarks
from paragraf.rules.validate import validate
from paragraf.textnorm import NOT_FOUND

MAX_VALUE = 300
MAX_LABEL = 120


def clean_value(spec: FieldSpec, value: str) -> str | None:
    """Значение, введённое или исправленное вручную, в виде карточки. None — пусто."""
    value = value.strip()[:MAX_VALUE]
    if not value or textnorm.compare_key(value) == NOT_FOUND:
        return None
    # «???» или «---» — не значение: без единой буквы или цифры поле считается пустым.
    if not any(char.isalnum() for char in value):
        return None
    cleaned = normalize(spec, textnorm.apply_choices(value, spec.choices))
    if cleaned is not None and spec.type == "person":
        cleaned = textnorm.to_nominative(cleaned)
    return cleaned


def restore_fields(doc_type: DocType, sent: list[CardField]) -> list[FieldValue]:
    """Поля известного типа в порядке описания, значения из присланной карточки."""
    by_key = {item.key: item for item in sent}
    fields: list[FieldValue] = []
    for spec in doc_type.fields:
        item = by_key.get(spec.key)
        if spec.is_mark:
            present = bool(item and item.value is True)
            value: str | bool = present
            found = present
            origin = "mark"
        else:
            text = item.value if item and isinstance(item.value, str) else ""
            cleaned = clean_value(spec, text)
            value = cleaned if cleaned is not None else NOT_FOUND
            found = cleaned is not None
            origin = "label"
        fields.append(
            FieldValue(
                key=spec.key,
                label=spec.label,
                type=spec.type,
                value=value,
                found=found,
                origin=origin,
                rule=spec.rule,
            )
        )
    return fields


def restore(doc_type: DocType, sent: list[CardField]) -> Analysis:
    fields = restore_fields(doc_type, sent)
    return Analysis(
        document_type=doc_type.id,
        document_title=doc_type.title,
        type_detected=False,
        ocr_engine="client",
        text="",
        fields=fields,
        validation=validate(doc_type, fields),
        remarks=find_remarks(doc_type, fields),
        width=0,
        height=0,
    )


def restore_other(sent: list[CardField], title: str | None) -> Analysis:
    """Документ незнакомого типа: карточка состоит из строк, найденных на снимке."""
    fields = [
        FieldValue(
            key=item.key,
            label=(item.label or item.key)[:MAX_LABEL],
            type="text",
            value=item.value[:MAX_VALUE],
            found=True,
            origin="generic",
        )
        for item in sent
        if isinstance(item.value, str) and item.value.strip()
    ]
    return Analysis(
        document_type=OTHER_TYPE,
        document_title=(title or "Документ").strip()[:MAX_LABEL],
        supported=False,
        type_detected=True,
        ocr_engine="client",
        text="",
        fields=fields,
        validation=Validation(status="not_applicable", missing_fields=[], sources=[]),
        width=0,
        height=0,
    )
