"""Поиск графических отметок: подписи и печати.

Проверяется только наличие рисунка. Слова «Подпись» и «М.П.» отметкой не
считаются: область с распознанным текстом вычитается перед анализом.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from paragraf.models import Box, Line


@dataclass
class Mark:
    present: bool
    box: Box | None = None
    score: float = 0.0


def ink_mask(color: np.ndarray) -> np.ndarray:
    """Маска «чернил»: всё, что заметно темнее фона вокруг."""
    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    kernel = max(15, (color.shape[1] // 60) | 1)
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((kernel, kernel), np.uint8))
    background = cv2.medianBlur(background, 21)
    diff = cv2.subtract(background, gray)
    _, mask = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
    return mask


def _erase_text(mask: np.ndarray, lines: list[Line], keep: Box | None = None) -> np.ndarray:
    """Стирает из маски распознанные слова, чтобы остались только рисунки."""
    height, width = mask.shape
    out = mask.copy()
    for line in lines:
        for word in line.words or []:
            if not _looks_like_text(word.text, word.confidence):
                continue
            box = word.box
            if keep is not None and _inside(box, keep):
                continue
            pad = int(0.004 * width)
            x0 = max(0, int(box.x * width) - pad)
            y0 = max(0, int(box.y * height) - pad)
            x1 = min(width, int((box.x + box.w) * width) + pad)
            y1 = min(height, int((box.y + box.h) * height) + pad)
            out[y0:y1, x0:x1] = 0
    return out


def _looks_like_text(text: str, confidence: float) -> bool:
    letters = sum(char.isalnum() for char in text)
    return letters >= 2 and confidence >= 0.55


def _inside(inner: Box, outer: Box) -> bool:
    cx, cy = inner.x + inner.w / 2, inner.y + inner.h / 2
    return outer.x <= cx <= outer.x + outer.w and outer.y <= cy <= outer.y + outer.h


def find_seal(color: np.ndarray, mask: np.ndarray | None = None) -> Mark:
    """Ищет круглую печать: крупное кольцо, не залитое внутри."""
    mask = ink_mask(color) if mask is None else mask
    height, width = mask.shape
    joined = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    # Внешний контур может оказаться рамкой по краю снимка, поэтому смотрим все контуры.
    contours, _ = cv2.findContours(joined, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    best = Mark(False)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if min(w, h) < 0.07 * width or max(w, h) > 0.45 * width:
            continue
        if not 0.6 <= w / h <= 1.67:
            continue
        coverage = _ring_coverage(joined, x, y, w, h)
        if coverage > best.score:
            best = Mark(
                coverage >= 0.6,
                Box(x=x / width, y=y / height, w=w / width, h=h / height),
                coverage,
            )
    return best


def _ring_coverage(mask: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    """Доля окружности, вписанной в рамку, на которой действительно есть линия."""
    cx, cy, rx, ry = x + w / 2, y + h / 2, w / 2, h / 2
    tolerance = max(2, int(0.035 * max(w, h)))
    thick = cv2.dilate(mask, np.ones((tolerance * 2 + 1, tolerance * 2 + 1), np.uint8))
    angles = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    xs = np.clip((cx + (rx - 1) * np.cos(angles)).astype(int), 0, mask.shape[1] - 1)
    ys = np.clip((cy + (ry - 1) * np.sin(angles)).astype(int), 0, mask.shape[0] - 1)
    return float(np.count_nonzero(thick[ys, xs]) / len(angles))


def find_signature(
    color: np.ndarray,
    lines: list[Line],
    anchor: Line | None,
    seal: Box | None = None,
    mask: np.ndarray | None = None,
) -> Mark:
    """Ищет росчерк рядом с меткой подписи.

    Линия для подписи убирается как длинный тонкий горизонтальный штрих. Если
    после этого в зоне остались штрихи заметной высоты, подпись есть.
    """
    mask = ink_mask(color) if mask is None else mask
    height, width = mask.shape
    text_height = _text_height(lines) * height

    if anchor is not None:
        box = anchor.box
        x0 = int((box.x + box.w) * width + 0.5 * text_height)
        x1 = int(min(width, x0 + 0.5 * width))
        cy = (box.y + box.h / 2) * height
        y0 = int(max(0, cy - 3.0 * text_height))
        y1 = int(min(height, cy + 2.2 * text_height))
    else:
        x0, x1, y0, y1 = 0, width, int(0.55 * height), height
    if x1 - x0 < 10 or y1 - y0 < 10:
        return Mark(False)

    work = _erase_text(mask, lines)
    if seal is not None:
        pad = int(0.12 * max(seal.w * width, seal.h * height))
        sx0, sy0 = int(seal.x * width) - pad, int(seal.y * height) - pad
        sx1, sy1 = int((seal.x + seal.w) * width) + pad, int((seal.y + seal.h) * height) + pad
        work[max(0, sy0) : sy1, max(0, sx0) : sx1] = 0
        # Печать стоит правее подписи: дальше её левого края росчерк не ищем.
        if anchor is not None and sx0 > x0 + 4 * text_height:
            x1 = min(x1, sx0)
    zone = work[y0:y1, x0:x1]

    rule_len = max(25, int(4 * text_height))
    rules = cv2.morphologyEx(zone, cv2.MORPH_OPEN, np.ones((1, rule_len), np.uint8))
    rules = cv2.dilate(rules, np.ones((3, 1), np.uint8))
    strokes = cv2.subtract(zone, rules)
    strokes = cv2.morphologyEx(strokes, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

    points = cv2.findNonZero(strokes)
    if points is None:
        return Mark(False)
    bx, by, bw, bh = cv2.boundingRect(points)
    amount = int(cv2.countNonZero(strokes))
    score = min(1.0, amount / max(1.0, 6 * text_height * text_height * 0.12))
    present = (
        bh >= 0.7 * text_height
        and bw >= 2.0 * text_height
        and amount >= 1.2 * text_height * text_height
    )
    box = Box(x=(x0 + bx) / width, y=(y0 + by) / height, w=bw / width, h=bh / height)
    return Mark(present, box if present else None, score)


def _text_height(lines: list[Line]) -> float:
    heights = sorted(
        word.box.h for line in lines for word in (line.words or []) if len(word.text) >= 3
    )
    return heights[len(heights) // 2] if heights else 0.014


def handwritten_zone(
    color: np.ndarray,
    mask: np.ndarray,
    lines: list[Line],
    label: Line,
    label_end: float,
) -> tuple[np.ndarray, Box] | None:
    """Вырезает место для значения справа от метки, если там что-то написано от руки.

    Чужие строки и линия для заполнения убираются. Если после этого чернил
    почти не осталось, поле пустое и возвращается None.
    """
    height, width = mask.shape
    text_height = _text_height(lines) * height
    center = (label.box.y + label.box.h / 2) * height
    x0 = int(label_end * width + 0.3 * text_height)
    x1 = int(0.97 * width)
    y0 = int(max(0, center - 1.7 * text_height))
    y1 = int(min(height, center + 1.5 * text_height))
    if x1 - x0 < 3 * text_height:
        return None

    others = [line for line in lines if line is not label]
    zone = _erase_text(mask, others)[y0:y1, x0:x1]
    rule_len = max(25, int(5 * text_height))
    rules = cv2.morphologyEx(zone, cv2.MORPH_OPEN, np.ones((1, rule_len), np.uint8))
    rules = cv2.dilate(rules, np.ones((3, 1), np.uint8))
    strokes = cv2.morphologyEx(cv2.subtract(zone, rules), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

    points = cv2.findNonZero(strokes)
    if points is None or cv2.countNonZero(strokes) < 2.0 * text_height * text_height:
        return None
    bx, by, bw, bh = cv2.boundingRect(points)
    if bh < 0.6 * text_height or bw < 1.5 * text_height:
        return None

    pad = int(0.4 * text_height)
    cx0, cy0 = max(0, x0 + bx - pad), max(0, y0 + by - pad)
    cx1, cy1 = min(width, x0 + bx + bw + pad), min(height, y0 + by + bh + pad)
    crop = color[cy0:cy1, cx0:cx1].copy()
    # Линию для заполнения закрашиваем цветом бумаги, чтобы она не мешала чтению.
    line_mask = np.zeros(mask.shape, np.uint8)
    line_mask[y0:y1, x0:x1] = rules
    paper = np.median(crop.reshape(-1, crop.shape[2]), axis=0)
    crop[line_mask[cy0:cy1, cx0:cx1] > 0] = paper
    box = Box(x=cx0 / width, y=cy0 / height, w=(cx1 - cx0) / width, h=(cy1 - cy0) / height)
    return crop, box
