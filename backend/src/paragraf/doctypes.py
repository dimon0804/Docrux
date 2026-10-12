"""Описания типов документов.

Каждый тип лежит в отдельном YAML-файле в ``config/doc_types``. Сервис читает
папку при старте, поэтому новый тип добавляется файлом, без правок кода.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

FieldType = Literal["text", "person", "date", "integer", "code", "mark"]
MarkKind = Literal["signature", "seal"]
CompositeKind = Literal["date_range", "number_and_date", "group_and_course"]


class FieldSpec(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    type: FieldType = "text"
    rule: str = Field(pattern=r"^\d+\.\d+$")
    mark: MarkKind | None = None
    aliases: list[str] = []
    ask: list[str] = []

    @model_validator(mode="after")
    def _mark_needs_kind(self) -> FieldSpec:
        if self.type == "mark" and self.mark is None:
            raise ValueError(f"поле {self.key}: для type=mark нужно указать mark")
        return self

    @property
    def is_mark(self) -> bool:
        return self.type == "mark"

    @property
    def labels(self) -> list[str]:
        return [self.label, *self.aliases]


class CompositeSpec(BaseModel):
    label: str
    kind: CompositeKind
    keys: list[str]
    aliases: list[str] = []

    @property
    def labels(self) -> list[str]:
        return [self.label, *self.aliases]


class DetectSpec(BaseModel):
    titles: list[str] = []
    keywords: list[str] = []


class DocType(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    title: str
    detect: DetectSpec = DetectSpec()
    fields: list[FieldSpec]
    composites: list[CompositeSpec] = []

    @model_validator(mode="after")
    def _check_keys(self) -> DocType:
        keys = [field.key for field in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError(f"тип {self.id}: ключи полей повторяются")
        for composite in self.composites:
            unknown = set(composite.keys) - set(keys)
            if unknown:
                raise ValueError(f"тип {self.id}: составная метка ссылается на {sorted(unknown)}")
        return self

    def field(self, key: str) -> FieldSpec:
        for spec in self.fields:
            if spec.key == key:
                return spec
        raise KeyError(key)

    @property
    def keys(self) -> list[str]:
        return [field.key for field in self.fields]

    @property
    def rules(self) -> list[str]:
        """Пункты Положения, которые задают обязательные поля и отметки."""
        seen: list[str] = []
        for field in self.fields:
            if field.rule not in seen:
                seen.append(field.rule)
        return sorted(seen, key=_rule_order)


def _rule_order(rule: str) -> tuple[int, ...]:
    return tuple(int(part) for part in rule.split("."))


class DocTypeRegistry:
    """Набор типов документов, загруженный из папки с конфигами."""

    def __init__(self, types: list[DocType]):
        self._types = {doc_type.id: doc_type for doc_type in types}

    @classmethod
    def load(cls, directory: Path) -> DocTypeRegistry:
        types: list[DocType] = []
        for path in sorted(directory.glob("*.y*ml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            try:
                types.append(DocType.model_validate(raw))
            except ValueError as exc:
                raise ValueError(f"{path.name}: {exc}") from exc
        if not types:
            raise FileNotFoundError(f"в {directory} нет описаний типов документов")
        ids = [doc_type.id for doc_type in types]
        if len(ids) != len(set(ids)):
            raise ValueError("идентификаторы типов документов повторяются")
        return cls(types)

    def get(self, type_id: str) -> DocType:
        try:
            return self._types[type_id]
        except KeyError:
            raise KeyError(f"неизвестный тип документа: {type_id}") from None

    def __contains__(self, type_id: str) -> bool:
        return type_id in self._types

    def __iter__(self):
        return iter(self._types.values())

    def __len__(self) -> int:
        return len(self._types)
