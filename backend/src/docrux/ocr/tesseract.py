"""Распознавание через Tesseract."""

from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np
import pytesseract

from docrux.models import Box, Line, OcrResult, Word
from docrux.ocr.base import group_lines, make_box

WEAK_WORD = 0.75
"""Ниже этой уверенности слова строка перечитывается отдельно."""
MAX_REREADS = 8


class TesseractEngine:
    name = "tesseract"

    def __init__(self, lang: str = "rus", psm: int = 6, tessdata: str | None = None):
        self.lang = lang
        self.psm = psm
        self.tessdata = tessdata or os.environ.get("DOCRUX_TESSDATA")
        command = os.environ.get("DOCRUX_TESSERACT_CMD")
        if command:
            pytesseract.pytesseract.tesseract_cmd = command

    def _config(self, psm: int | None = None) -> str:
        parts = [f"--psm {psm or self.psm}", "--oem 1", "-c preserve_interword_spaces=1"]
        if self.tessdata and Path(self.tessdata).is_dir():
            parts.insert(0, f"--tessdata-dir {self.tessdata}")
        return " ".join(parts)

    def _read(self, gray: np.ndarray, psm: int) -> OcrResult:
        height, width = gray.shape[:2]
        data = pytesseract.image_to_data(
            gray, lang=self.lang, config=self._config(psm), output_type=pytesseract.Output.DICT
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

    def recognize(self, gray: np.ndarray) -> OcrResult:
        result = self._read(gray, self.psm)
        return self._reread_weak_lines(gray, result)

    def _reread_weak_lines(self, gray: np.ndarray, result: OcrResult) -> OcrResult:
        """Перечитывает по отдельности строки бланка, в которых движок не уверен.

        На блике или в тени разметка страницы целиком иногда теряет конец строки:
        от «Жанна Петровна» остаётся «Жанна П». Та же строка, поданная отдельно,
        читается полностью. Новое чтение принимается, только если оно увереннее
        прежнего и не короче его.
        """
        height = gray.shape[0]
        lines = list(result.lines)
        budget = MAX_REREADS
        for index, line in enumerate(lines):
            if budget == 0:
                break
            if ":" not in line.text or len(line.words) < 2:
                continue
            weakest = min(word.confidence for word in line.words)
            if weakest >= WEAK_WORD:
                continue
            middle = line.box.y + line.box.h / 2
            alone = all(
                other is line or not (other.box.y <= middle <= other.box.y + other.box.h)
                for other in lines
            )
            if not alone:
                continue
            top = max(int((line.box.y - line.box.h * 0.6) * height), 0)
            bottom = min(int((line.box.y + line.box.h * 1.6) * height), height)
            if bottom - top < 8:
                continue
            budget -= 1
            again = self._read(gray[top:bottom], 7)
            words = [word for other in again.lines for word in other.words]
            if len(words) < len(line.words) or ":" not in " ".join(word.text for word in words):
                continue
            if min(word.confidence for word in words) <= weakest:
                continue
            share = (bottom - top) / height
            moved = [
                word.model_copy(
                    update={
                        "box": Box(
                            x=word.box.x,
                            y=top / height + word.box.y * share,
                            w=word.box.w,
                            h=word.box.h * share,
                        )
                    }
                )
                for word in sorted(words, key=lambda word: word.box.x)
            ]
            box = moved[0].box
            for word in moved[1:]:
                box = box.union(word.box)
            lines[index] = Line(
                text=" ".join(word.text for word in moved),
                box=box,
                words=moved,
                confidence=sum(word.confidence for word in moved) / len(moved),
            )
        return result.model_copy(update={"lines": lines})

    def available(self) -> bool:
        try:
            return self.lang in pytesseract.get_languages(config=self._config())
        except Exception:
            return False
