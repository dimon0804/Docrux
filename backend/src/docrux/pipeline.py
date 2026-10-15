"""Сквозной путь: файл → текст → карточка → проверка → ответ."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import numpy as np

from docrux import textnorm
from docrux.doctypes import DocType, DocTypeRegistry
from docrux.extraction import freeform
from docrux.extraction.classify import detect_type
from docrux.extraction.fields import Found, locate, normalize, split_composite
from docrux.extraction.generic import OTHER_TYPE, generic_fields, guess_title
from docrux.imaging import advice, marks
from docrux.imaging.loader import Page, load_page, load_pages
from docrux.imaging.preprocess import Prepared, prepare
from docrux.models import Analysis, Answer, Box, FieldValue, Line, OcrResult, Validation
from docrux.ocr.base import OcrEngine
from docrux.ocr.handwriting import HandwritingReader
from docrux.qa.answerer import COMPLETENESS_QUESTION, Answerer
from docrux.qa.retrieval import load_hints
from docrux.rules.kb import RuleBook
from docrux.rules.remarks import find_remarks
from docrux.rules.validate import validate
from docrux.settings import Settings, get_settings
from docrux.textnorm import NOT_FOUND

FORM_SHARE = 0.6
"""Доля полей с метками, начиная с которой документ считается бланком."""
PRINTED_TRUST = 0.6
GARBAGE_TRUST = 0.3
"""Ниже этой уверенности печатное чтение считается случайным набором букв."""
"""Ниже этой уверенности печатное значение перепроверяется как рукописное."""
HINT_MIN_WIDTH = 0.25
"""Ширина подсказки, если после метки на строке ничего нет, в долях ширины снимка."""


class TypeNotDetected(ValueError):
    """Тип документа не удалось определить автоматически."""


@dataclass
class Processed:
    analysis: Analysis
    image: np.ndarray
    """Выровненный снимок, к которому привязаны рамки полей."""


class Pipeline:
    def __init__(
        self,
        registry: DocTypeRegistry,
        rulebook: RuleBook,
        engine: OcrEngine,
        settings: Settings | None = None,
    ):
        self.registry = registry
        self.rulebook = rulebook
        self.engine = engine
        self.settings = settings or get_settings()
        self.answerer = Answerer(rulebook, load_hints(self.settings.hints_path))
        self.handwriting = HandwritingReader.load(self.settings.handwriting_model)

    @classmethod
    def default(cls, settings: Settings | None = None) -> Pipeline:
        from docrux.ocr.tesseract import TesseractEngine

        settings = settings or get_settings()
        return cls(
            DocTypeRegistry.load(settings.doc_types_dir),
            RuleBook.load(settings.rules_path),
            TesseractEngine(settings.ocr_lang, settings.ocr_psm, settings.tessdata),
            settings,
        )

    def read(self, data: bytes | list[bytes]) -> tuple[Page, Prepared, OcrResult, list[float]]:
        """Готовит и распознаёт все страницы, затем склеивает их в один длинный снимок.

        Возвращает документ, склеенный снимок, общий текст и границы страниц
        в долях высоты. Рамки слов пересчитаны в координаты склеенного снимка.
        """
        started = time.perf_counter()
        page = load_pages(data) if isinstance(data, list) else load_page(data)
        loaded = time.perf_counter()
        spent_prepare = spent_ocr = 0.0
        use_layer = self.settings.pdf_text_layer == "prefer" and page.has_text_layer
        prepared_pages: list[Prepared] = []
        results: list[OcrResult] = []
        for index, image in enumerate(page.images):
            if use_layer:
                # Рамки текстового слоя привязаны к исходной странице: геометрию не трогаем.
                prepared = Prepared(color=image, gray=_gray(image), quality={"pdf_text": True})
                height, width = image.shape[:2]
                result = OcrResult(
                    engine="pdf-text", lines=page.embedded[index], width=width, height=height
                )
            else:
                mark = time.perf_counter()
                prepared = prepare(image)
                spent_prepare += time.perf_counter() - mark
                mark = time.perf_counter()
                result = self.engine.recognize(prepared.gray)
                spent_ocr += time.perf_counter() - mark
            prepared_pages.append(prepared)
            results.append(result)
        if len(prepared_pages) == 1:
            joined, ocr, breaks = prepared_pages[0], results[0], []
        else:
            joined, ocr, breaks = _stack(prepared_pages, results)
        # Сколько занял каждый шаг: интерфейс показывает ход разбора.
        joined.quality["ms_load"] = round((loaded - started) * 1000)
        joined.quality["ms_prepare"] = round(spent_prepare * 1000)
        joined.quality["ms_ocr"] = round(spent_ocr * 1000)
        return page, joined, ocr, breaks

    def analyze(self, data: bytes | list[bytes], type_id: str | None = None) -> Processed:
        page, prepared, ocr, breaks = self.read(data)

        mark = time.perf_counter()
        detected, confidence = detect_type(self.registry, ocr.lines)
        quality = dict(prepared.quality)
        quality["ms_detect"] = round((time.perf_counter() - mark) * 1000)
        quality["ocr_lines"] = len(ocr.lines)
        quality["ocr_words"] = sum(len(line.words) for line in ocr.lines)
        if not quality.get("pdf_text"):
            quality.update(advice.text_stats(prepared.gray, ocr.lines))
        quality["file_kind"] = page.kind
        quality["pages"] = page.pages
        tips = advice.advise(quality)
        if type_id:
            doc_type = self.registry.get(type_id)
        elif detected is not None:
            doc_type = detected
        else:
            # Документ не похож ни на один известный тип: показываем текст и найденные пары.
            fields = generic_fields(ocr.lines)
            analysis = Analysis(
                document_type=OTHER_TYPE,
                document_title=guess_title(ocr.lines),
                supported=False,
                type_detected=True,
                type_confidence=round(confidence, 3),
                ocr_engine=ocr.engine,
                text=ocr.text,
                fields=fields,
                validation=Validation(status="not_applicable", missing_fields=[], sources=[]),
                quality=quality,
                advice=tips,
                page_breaks=breaks,
                width=prepared.color.shape[1],
                height=prepared.color.shape[0],
            )
            return Processed(analysis=analysis, image=prepared.color)

        mark = time.perf_counter()
        fields = self.extract(doc_type, ocr.lines, prepared.color)
        quality["ms_extract"] = round((time.perf_counter() - mark) * 1000)
        analysis = Analysis(
            document_type=doc_type.id,
            document_title=doc_type.title,
            type_detected=type_id is None,
            type_confidence=round(confidence, 3),
            ocr_engine=ocr.engine,
            text=ocr.text,
            fields=fields,
            validation=validate(doc_type, fields),
            remarks=find_remarks(doc_type, fields),
            quality=quality,
            advice=tips,
            page_breaks=breaks,
            width=prepared.color.shape[1],
            height=prepared.color.shape[0],
        )
        return Processed(analysis=analysis, image=prepared.color)

    def extract(self, doc_type: DocType, lines: list[Line], color: np.ndarray) -> list[FieldValue]:
        located = locate(doc_type, lines)
        raw: dict[str, Found] = {}
        for composite in doc_type.composites:
            hit = located.get("+".join(composite.keys))
            if hit is None:
                continue
            for key, value in split_composite(composite, hit.raw).items():
                raw[key] = Found(value, hit.box, hit.confidence, hit.label_line, hit.label_end)
        for key, hit in located.items():
            if "+" not in key:
                raw[key] = hit

        # Поля без метки на документе ищем в свободном тексте по образцам фраз.
        text_keys = [spec.key for spec in doc_type.fields if not spec.is_mark]
        labeled = sum(key in raw for key in text_keys)
        form_like = labeled >= FORM_SHARE * len(text_keys)
        if form_like:
            # Бланк: пустое поле с меткой остаётся пустым, ищем только поля без метки.
            unlabeled = {key for key in text_keys if key not in raw}
        else:
            # Связный текст: одиночная «метка» может оказаться подписью под документом.
            unlabeled = {
                key for key in text_keys if key not in raw or textnorm.is_blank(raw[key].raw)
            }
        free = freeform.find(doc_type, lines, unlabeled)

        mask = marks.ink_mask(color)
        seal = marks.find_seal(color, mask)
        height, width = color.shape[:2]

        fields: list[FieldValue] = []
        for spec in doc_type.fields:
            hit = raw.get(spec.key)
            if spec.is_mark:
                if spec.mark == "seal":
                    mark = seal
                    anchor = hit.label_line if hit else _seal_anchor(lines)
                    hint = marks.seal_zone(anchor, width, height) if anchor else None
                else:
                    anchor = hit.label_line if hit else None
                    mark = marks.find_signature(
                        color, lines, anchor, seal.box if seal.present else None, mask
                    )
                    hint = marks.signature_zone(lines, anchor, width, height) if anchor else None
                fields.append(
                    FieldValue(
                        key=spec.key,
                        label=spec.label,
                        type=spec.type,
                        value=mark.present,
                        found=mark.present,
                        box=mark.box if mark.present else None,
                        hint_box=hint if not mark.present else None,
                        confidence=round(mark.score, 3),
                        origin="mark",
                        rule=spec.rule,
                    )
                )
                continue
            value = normalize(spec, textnorm.apply_choices(hit.raw, spec.choices)) if hit else None
            box = hit.box if hit and value is not None else None
            confidence = hit.confidence if hit else None
            handwritten = False
            origin = "label"
            loose = free.get(spec.key)
            if value is None and loose is not None:
                found_raw = textnorm.apply_choices(loose.raw, spec.choices)
                value = normalize(spec, found_raw)
                if value is not None and spec.type == "person":
                    value = textnorm.to_nominative(value)
                if value is not None:
                    box, confidence, origin = loose.box, loose.confidence, "text"
            guess = None
            if hit and self.handwriting and (value is None or hit.confidence < PRINTED_TRUST):
                # Печатного значения нет или оно ненадёжно: возможно, поле заполнено от руки.
                zone = marks.handwritten_zone(color, mask, lines, hit.label_line, hit.label_end)
                if zone is not None:
                    text, score = self.handwriting.read(zone[0])
                    written = normalize(spec, textnorm.apply_choices(text, spec.choices))
                    if written is not None and value is not None and _same(written, value):
                        # Два независимых чтения совпали: значению можно верить.
                        handwritten = True
                        box, confidence = zone[1], max(score, hit.confidence)
                    elif value is None or hit.confidence < GARBAGE_TRUST:
                        # Почерк читается ненадёжно, а выдумывать нельзя: поле остаётся
                        # пустым, чтение модели показывается только как подсказка.
                        handwritten = True
                        guess = written
                        value, box, confidence = None, zone[1], score
            fields.append(
                FieldValue(
                    key=spec.key,
                    label=spec.label,
                    type=spec.type,
                    value=value if value is not None else NOT_FOUND,
                    found=value is not None,
                    raw=hit.raw if hit else (loose.raw if loose else None),
                    box=box,
                    hint_box=_value_place(hit) if hit and value is None else None,
                    confidence=round(confidence, 3) if confidence is not None else None,
                    handwritten=handwritten,
                    guess=guess,
                    origin=origin,
                    rule=spec.rule,
                )
            )
        return fields

    def empty(self, type_id: str) -> Analysis:
        """Карточка, в которой ничего не найдено: для файла, который не удалось прочитать."""
        doc_type = self.registry.get(type_id)
        fields = [
            FieldValue(
                key=spec.key,
                label=spec.label,
                type=spec.type,
                value=False if spec.is_mark else NOT_FOUND,
                found=False,
                origin="mark" if spec.is_mark else "label",
                rule=spec.rule,
            )
            for spec in doc_type.fields
        ]
        return Analysis(
            document_type=doc_type.id,
            document_title=doc_type.title,
            type_detected=False,
            ocr_engine="none",
            text="",
            fields=fields,
            validation=validate(doc_type, fields),
            width=0,
            height=0,
        )

    def _type(self, analysis: Analysis) -> DocType | None:
        return self.registry.get(analysis.document_type) if analysis.supported else None

    def ask(self, analysis: Analysis, question: str, assistant: bool = False) -> Answer:
        """Отвечает на вопрос. assistant включает рассказ о документе и поиск по Положению."""
        return self.answerer.answer(self._type(analysis), analysis, question, assistant)

    def check(self, analysis: Analysis) -> Answer:
        doc_type = self._type(analysis)
        if doc_type is None:
            return self.answerer.answer(None, analysis, COMPLETENESS_QUESTION)
        return self.answerer.with_trace(
            doc_type, analysis, self.answerer.completeness(doc_type, analysis)
        )


def _stack(
    pages: list[Prepared], results: list[OcrResult]
) -> tuple[Prepared, OcrResult, list[float]]:
    """Склеивает страницы по вертикали и переносит рамки слов в общие координаты."""
    import cv2

    width = max(item.color.shape[1] for item in pages)
    colors, grays = [], []
    for item in pages:
        scale = width / item.color.shape[1]
        if item.color.shape[1] != width:
            size = (width, round(item.color.shape[0] * scale))
            colors.append(cv2.resize(item.color, size, interpolation=cv2.INTER_CUBIC))
            grays.append(cv2.resize(item.gray, size, interpolation=cv2.INTER_CUBIC))
        else:
            colors.append(item.color)
            grays.append(item.gray)
    total = sum(image.shape[0] for image in colors)

    lines: list[Line] = []
    breaks: list[float] = []
    offset = 0
    for image, result in zip(colors, results, strict=True):
        share, top = image.shape[0] / total, offset / total

        def move(box: Box, share: float = share, top: float = top) -> Box:
            return Box(x=box.x, y=top + box.y * share, w=box.w, h=box.h * share)

        for line in result.lines:
            words = [word.model_copy(update={"box": move(word.box)}) for word in line.words]
            lines.append(line.model_copy(update={"box": move(line.box), "words": words}))
        offset += image.shape[0]
        breaks.append(offset / total)

    quality = dict(pages[0].quality)
    merged = Prepared(color=np.vstack(colors), gray=np.vstack(grays), quality=quality)
    ocr = OcrResult(engine=results[0].engine, lines=lines, width=width, height=total)
    return merged, ocr, breaks[:-1]


def _value_place(hit: Found) -> Box:
    """Где на снимке должно стоять значение пустого поля: правее метки до конца строки."""
    line = hit.label_line.box
    x0 = min(hit.label_end + 0.005, 0.95)
    x1 = min(max(line.x + line.w, x0 + HINT_MIN_WIDTH), 0.97)
    pad = 0.15 * line.h
    return Box(x=x0, y=max(0.0, line.y - pad), w=max(x1 - x0, 0.02), h=line.h + 2 * pad)


_SEAL_LABEL = re.compile(r"^\s*(м\.?\s*п\.?|место\s+печати)\s*$", re.IGNORECASE)


def _seal_anchor(lines: list[Line]) -> Line | None:
    """Строка «М.П.»: возле неё должна стоять печать."""
    return next((line for line in lines if _SEAL_LABEL.match(line.text)), None)


def _same(left: str, right: str) -> bool:
    return textnorm.compare_key(left) == textnorm.compare_key(right)


def _gray(image: np.ndarray) -> np.ndarray:
    import cv2

    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
