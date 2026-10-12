"""Сквозной путь: файл → текст → карточка → проверка → ответ."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from paragraf.doctypes import DocType, DocTypeRegistry
from paragraf.extraction.classify import detect_type
from paragraf.extraction.fields import Found, locate, normalize, split_composite
from paragraf.imaging import marks
from paragraf.imaging.loader import Page, load_page
from paragraf.imaging.preprocess import Prepared, prepare
from paragraf.models import Analysis, Answer, Box, FieldValue, Line, OcrResult
from paragraf.ocr.base import OcrEngine
from paragraf.qa.answerer import Answerer
from paragraf.rules.kb import RuleBook
from paragraf.rules.validate import validate
from paragraf.settings import Settings, get_settings
from paragraf.textnorm import NOT_FOUND


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
        self.answerer = Answerer(rulebook)

    @classmethod
    def default(cls, settings: Settings | None = None) -> Pipeline:
        from paragraf.ocr.tesseract import TesseractEngine

        settings = settings or get_settings()
        return cls(
            DocTypeRegistry.load(settings.doc_types_dir),
            RuleBook.load(settings.rules_path),
            TesseractEngine(settings.ocr_lang, settings.ocr_psm, settings.tessdata),
            settings,
        )

    def read(self, data: bytes) -> tuple[Page, Prepared, OcrResult, list[float]]:
        """Готовит и распознаёт все страницы, затем склеивает их в один длинный снимок.

        Возвращает документ, склеенный снимок, общий текст и границы страниц
        в долях высоты. Рамки слов пересчитаны в координаты склеенного снимка.
        """
        page = load_page(data)
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
                prepared = prepare(image)
                result = self.engine.recognize(prepared.gray)
            prepared_pages.append(prepared)
            results.append(result)
        if len(prepared_pages) == 1:
            return page, prepared_pages[0], results[0], []
        return (page, *_stack(prepared_pages, results))

    def analyze(self, data: bytes, type_id: str | None = None) -> Processed:
        page, prepared, ocr, breaks = self.read(data)

        detected, confidence = detect_type(self.registry, ocr.lines)
        if type_id:
            doc_type = self.registry.get(type_id)
        elif detected is not None:
            doc_type = detected
        else:
            raise TypeNotDetected("Не удалось определить тип документа. Выберите его вручную.")

        fields = self.extract(doc_type, ocr.lines, prepared.color)
        quality = dict(prepared.quality)
        quality["file_kind"] = page.kind
        quality["pages"] = page.pages
        analysis = Analysis(
            document_type=doc_type.id,
            document_title=doc_type.title,
            type_detected=type_id is None,
            type_confidence=round(confidence, 3),
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

    def extract(self, doc_type: DocType, lines: list[Line], color: np.ndarray) -> list[FieldValue]:
        located = locate(doc_type, lines)
        raw: dict[str, Found] = {}
        for composite in doc_type.composites:
            hit = located.get("+".join(composite.keys))
            if hit is None:
                continue
            for key, value in split_composite(composite, hit.raw).items():
                raw[key] = Found(value, hit.box, hit.confidence, hit.label_line)
        for key, hit in located.items():
            if "+" not in key:
                raw[key] = hit

        mask = marks.ink_mask(color)
        seal = marks.find_seal(color, mask)

        fields: list[FieldValue] = []
        for spec in doc_type.fields:
            hit = raw.get(spec.key)
            if spec.is_mark:
                if spec.mark == "seal":
                    mark = seal
                else:
                    anchor = hit.label_line if hit else None
                    mark = marks.find_signature(
                        color, lines, anchor, seal.box if seal.present else None, mask
                    )
                fields.append(
                    FieldValue(
                        key=spec.key,
                        label=spec.label,
                        type=spec.type,
                        value=mark.present,
                        found=mark.present,
                        box=mark.box if mark.present else None,
                        confidence=round(mark.score, 3),
                        rule=spec.rule,
                    )
                )
                continue
            value = normalize(spec, hit.raw) if hit else None
            fields.append(
                FieldValue(
                    key=spec.key,
                    label=spec.label,
                    type=spec.type,
                    value=value if value is not None else NOT_FOUND,
                    found=value is not None,
                    raw=hit.raw if hit else None,
                    box=hit.box if hit and value is not None else None,
                    confidence=round(hit.confidence, 3) if hit else None,
                    rule=spec.rule,
                )
            )
        return fields

    def ask(self, analysis: Analysis, question: str) -> Answer:
        return self.answerer.answer(self.registry.get(analysis.document_type), analysis, question)

    def check(self, analysis: Analysis) -> Answer:
        return self.answerer.completeness(self.registry.get(analysis.document_type), analysis)


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


def _gray(image: np.ndarray) -> np.ndarray:
    import cv2

    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
