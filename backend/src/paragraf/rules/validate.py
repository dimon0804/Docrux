"""Предварительная проверка комплектности документа."""

from __future__ import annotations

from paragraf.doctypes import DocType
from paragraf.models import FieldValue, Validation


def _order(rule: str) -> tuple[int, ...]:
    return tuple(int(part) for part in rule.split("."))


def validate(doc_type: DocType, fields: list[FieldValue]) -> Validation:
    """Сверяет карточку с обязательными полями типа.

    Для полного документа возвращаются все пункты, задающие обязательные поля
    и отметки. Для неполного — только пункты, которые требуют недостающее.
    """
    missing = [field.key for field in fields if not field.found]
    if not missing:
        rules = doc_type.rules
        status = "document_ok"
    else:
        rules = sorted({doc_type.field(key).rule for key in missing}, key=_order)
        status = "missing_fields"
    return Validation(
        status=status,
        missing_fields=missing,
        sources=[f"rule:{rule}" for rule in rules],
    )
