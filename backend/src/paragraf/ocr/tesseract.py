"""Распознавание через Tesseract."""

from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np
import pytesseract

from paragraf.models import OcrResult, Word
from paragraf.ocr.base import group_lines, make_box


class TesseractEngine:
    name = "tesseract"

    def __init__(self, lang: str = "rus", psm: int = 6, tessdata: str | None = None):
        self.lang = lang
        self.psm = psm
        self.tessdata = tessdata or os.environ.get("PARAGRAF_TESSDATA")
        command = os.environ.get("PARAGRAF_TESSERACT_CMD")
        if command:
            pytesseract.pytesseract.tesseract_cmd = command

    def _config(self) -> str:
        parts = [f"--psm {self.psm}", "--oem 1", "-c preserve_interword_spaces=1"]
        if self.tessdata and Path(self.tessdata).is_dir():
            parts.insert(0, f"--tessdata-dir {self.tessdata}")
        return " ".join(parts)

    def recognize(self, gray: np.ndarray) -> OcrResult:
        height, width = gray.shape[:2]
        data = pytesseract.image_to_data(
            gray, lang=self.lang, config=self._config(), output_type=pytesseract.Output.DICT
        )
        words: list[Word] = []
        for index, text in enumerate(data["text"]):
            text = text.strip()
            confidence = float(data["conf"][index])
            if not text or confidence < 0:
                continue
            if not re.search(r"[0-9A-Za-zА-Яа-яЁё_№]", text):
                continue
            box = make_box(
                data["left"][index],
                data["top"][index],
                data["width"][index],
                data["height"][index],
                width,
                height,
            )
            words.append(Word(text=text, box=box, confidence=confidence / 100))
        return group_lines(words, self.name, width, height)

    def available(self) -> bool:
        try:
            return self.lang in pytesseract.get_languages(config=self._config())
        except Exception:
            return False
