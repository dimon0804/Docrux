"""Схемы запросов и ответов HTTP API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from paragraf.models import Analysis, Answer


class FieldInfo(BaseModel):
    key: str
    label: str
    type: str
    rule: str


class DocTypeInfo(BaseModel):
    id: str
    title: str
    fields: list[FieldInfo]
    rules: list[str]


class RuleInfo(BaseModel):
    number: str
    section: str
    text: str


class AnalyzeResponse(BaseModel):
    analysis: Analysis
    check: Answer
    answer: Answer | None = None
    image: str = Field(description="Выровненный снимок: data URL в формате JPEG")


class CardField(BaseModel):
    key: str = Field(max_length=64)
    value: str | bool
    found: bool
    label: str | None = Field(default=None, max_length=120)


class AskRequest(BaseModel):
    document_type: str = Field(max_length=64)
    document_title: str | None = Field(default=None, max_length=120)
    fields: list[CardField] = Field(max_length=64)
    question: str = Field(min_length=1, max_length=500)


class Problem(BaseModel):
    detail: str
    code: str
