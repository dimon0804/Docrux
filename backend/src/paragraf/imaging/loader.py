"""Приём файла: проверка формата и превращение в изображение страницы."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import cv2
import numpy as np
import pymupdf as fitz
from PIL import Image, ImageOps

from paragraf.models import Box, Line, Word

MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 50_000_000
PDF_DPI = 200
MAX_PAGES = 10

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class UnsupportedFile(ValueError):
    """Файл не подходит: не тот формат, слишком большой или повреждён."""


@dataclass
class Page:
    """Загруженный документ: одна страница у фото, одна или несколько у PDF."""

    images: list[np.ndarray]
    """Страницы в BGR."""
    kind: str
    """jpeg, png или pdf."""
    embedded: list[list[Line]] = field(default_factory=list)
    """Текстовый слой каждой страницы PDF, если он есть."""

    @property
    def pages(self) -> int:
        return len(self.images)

    @property
    def has_text_layer(self) -> bool:
        return len(self.embedded) == len(self.images) and any(self.embedded)


def sniff(data: bytes) -> str:
    """Определяет формат по сигнатуре, а не по расширению или Content-Type."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b"%PDF-" in data[:1024]:
        return "pdf"
    raise UnsupportedFile("Поддерживаются только JPG, PNG и PDF.")


def load_page(data: bytes) -> Page:
    if not data:
        raise UnsupportedFile("Файл пустой.")
    if len(data) > MAX_BYTES:
        raise UnsupportedFile("Файл больше 15 МБ.")
    kind = sniff(data)
    return _load_pdf(data) if kind == "pdf" else _load_image(data, kind)


def _load_image(data: bytes, kind: str) -> Page:
    try:
        with Image.open(io.BytesIO(data)) as raw:
            raw.verify()
        with Image.open(io.BytesIO(data)) as raw:
            if raw.width * raw.height > MAX_PIXELS:
                raise UnsupportedFile("Изображение слишком большое.")
            picture = ImageOps.exif_transpose(raw).convert("RGB")
    except UnsupportedFile:
        raise
    except Exception as exc:  # Pillow бросает разные исключения на битых файлах
        raise UnsupportedFile("Не удалось прочитать изображение.") from exc
    image = cv2.cvtColor(np.asarray(picture), cv2.COLOR_RGB2BGR)
    if min(image.shape[:2]) < 200:
        raise UnsupportedFile("Изображение слишком маленькое, текст не прочитать.")
    return Page(images=[image], kind=kind)


def _load_pdf(data: bytes) -> Page:
    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise UnsupportedFile("Не удалось открыть PDF.") from exc
    with document:
        if document.needs_pass:
            raise UnsupportedFile("PDF защищён паролем.")
        if document.page_count < 1:
            raise UnsupportedFile("В PDF нет страниц.")
        if document.page_count > MAX_PAGES:
            raise UnsupportedFile(f"В PDF больше {MAX_PAGES} страниц.")
        zoom = PDF_DPI / 72
        images: list[np.ndarray] = []
        embedded: list[list[Line]] = []
        total = 0.0
        for page in document:
            rect = page.rect
            total += rect.width * rect.height * zoom * zoom
            if total > MAX_PIXELS * 2:
                raise UnsupportedFile("Страницы PDF слишком большие.")
            pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            images.append(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            embedded.append(_embedded_lines(page, rect.width, rect.height))
        return Page(images=images, kind="pdf", embedded=embedded)


def _embedded_lines(page: fitz.Page, width: float, height: float) -> list[Line]:
    """Текстовый слой PDF в том же виде, в каком его отдаёт OCR."""
    grouped: dict[tuple[int, int], list[Word]] = {}
    for x0, y0, x1, y1, text, block, line, _ in page.get_text("words"):
        box = Box(x=x0 / width, y=y0 / height, w=(x1 - x0) / width, h=(y1 - y0) / height)
        grouped.setdefault((block, line), []).append(Word(text=text, box=box))
    lines = []
    for words in grouped.values():
        box = words[0].box
        for word in words[1:]:
            box = box.union(word.box)
        lines.append(Line(text=" ".join(word.text for word in words), box=box, words=words))
    lines.sort(key=lambda item: (round(item.box.y, 3), item.box.x))
    return lines
