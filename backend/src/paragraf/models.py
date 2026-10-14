"""Структуры данных, которыми обмениваются шаги пайплайна."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Status = Literal["document_ok", "missing_fields", "not_applicable"]


class Box(BaseModel):
    """Прямоугольник на нормализованном снимке, в долях ширины и высоты (0..1)."""

    x: float
    y: float
    w: float
    h: float

    def union(self, other: Box) -> Box:
        x0, y0 = min(self.x, other.x), min(self.y, other.y)
        x1 = max(self.x + self.w, other.x + other.w)
        y1 = max(self.y + self.h, other.y + other.h)
        return Box(x=x0, y=y0, w=x1 - x0, h=y1 - y0)


class Word(BaseModel):
    text: str
    box: Box
    confidence: float = 1.0


class Line(BaseModel):
    text: str
    box: Box
    words: list[Word] = []
    confidence: float = 1.0


class OcrResult(BaseModel):
    """Распознанный текст страницы."""

    engine: str
    lines: list[Line]
    width: int
    height: int

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


class FieldValue(BaseModel):
    """Одно поле карточки."""

    key: str
    label: str
    type: str
    value: str | bool
    found: bool
    raw: str | None = None
    box: Box | None = None
    hint_box: Box | None = None
    """Где должно было стоять пустое поле или отметка: правее найденной метки."""
    confidence: float | None = None
    handwritten: bool = False
    """Поле заполнено от руки."""
    guess: str | None = None
    """Как рукописное значение прочитала модель. Это подсказка, а не факт."""
    origin: Literal["label", "text", "mark", "generic"] = "label"
    """Откуда взято значение: строка с меткой, свободный текст, рисунок или нераспознанный тип."""
    rule: str = ""


class Remark(BaseModel):
    """Замечание для сотрудника: на итог проверки по Положению не влияет."""

    text: str
    fields: list[str] = []


class Validation(BaseModel):
    status: Status
    missing_fields: list[str]
    sources: list[str]


class Answer(BaseModel):
    question: str
    intent: str
    answerable: bool
    value: str | None
    answer: str
    sources: list[str]
    highlight: list[str] = []
    """Ключи полей, которые стоит подсветить на снимке."""
    trace: list[str] = []
    """Почему ответ такой: шаги рассуждения для интерфейса."""


class Analysis(BaseModel):
    """Полный результат разбора одного документа."""

    document_type: str
    document_title: str
    supported: bool = True
    """Относится ли документ к типам, которые описывает Положение."""
    type_detected: bool
    type_confidence: float | None = None
    ocr_engine: str
    text: str
    fields: list[FieldValue]
    validation: Validation
    quality: dict[str, float | str | bool] = {}
    advice: list[str] = []
    remarks: list[Remark] = []
    """Советы по съёмке, если снимок мешал распознаванию."""
    page_breaks: list[float] = []
    """Границы страниц на склеенном снимке, в долях высоты."""
    width: int
    height: int

    def field(self, key: str) -> FieldValue:
        for item in self.fields:
            if item.key == key:
                return item
        raise KeyError(key)

    def card(self) -> dict[str, str | bool]:
        """Карточка в формате results.json."""
        return {item.key: item.value for item in self.fields}
