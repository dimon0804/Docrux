"""Советы студенту по съёмке: что мешало прочитать снимок и как переснять лучше.

Пороги подобраны на наборах открытого пакета: на чистых сканах (open, synth) ни
один совет не срабатывает, на испорченных снимках срабатывает соответствующий.
Совет даётся, только если студент может что-то исправить сам.
"""

from __future__ import annotations

import numpy as np

from paragraf.models import Line

LOW_RESOLUTION_UPSCALE = 2.0
"""Снимок пришлось увеличить хотя бы вдвое: лист уже 850 точек. У чистых сканов 1.5."""
BLUR_SHARPNESS = 40.0
"""Резкость (дисперсия лапласиана) ниже этой: снимок смазан. У чистых сканов больше 230."""
UNEVEN_LIGHT = 0.1
"""Разброс яркости фона, начиная с которого на листе видна тень. Выравнивание включается с 0.06."""
FADED_CONTRAST = 185.0
"""Средний контраст слов ниже этого: текст засвечен бликом. У чистых сканов около 230,
у обычных фото не ниже 195. Смаз и увеличение тоже снижают контраст, их здесь не учитываем."""
STRONG_SKEW = 3.0
"""Наклон текста в градусах, после которого стоит держать телефон ровнее. У ровных до 1.6."""
WEAK_WORD = 0.7
WEAK_SHARE = 0.12
"""Доля неуверенно прочитанных слов, при которой снимок стоит переснять. У чистых до 0.07."""

LOW_RESOLUTION = (
    "Снимок слишком мелкий: подойдите ближе, чтобы лист занял весь кадр, "
    "или отправьте фото в полном размере."
)
BLURRY = "Снимок нечёткий: держите телефон неподвижно и снимайте при хорошем свете."
SHADOW = (
    "На листе тень или неровный свет: снимайте при ровном освещении "
    "и не заслоняйте лист телефоном или рукой."
)
GLARE = "Часть текста засвечена бликом: выключите вспышку или чуть измените угол съёмки."
TILTED = "Лист снят с наклоном: держите телефон ровно над листом."
WEAK_TEXT = (
    "Часть текста читается неуверенно: переснимите лист ровно, при хорошем свете, "
    "чтобы он занял весь кадр."
)


def text_stats(gray: np.ndarray, lines: list[Line]) -> dict[str, float]:
    """Контраст слов и доля неуверенно прочитанных: дополняют сведения о качестве снимка."""
    height, width = gray.shape[:2]
    contrasts: list[float] = []
    confidences: list[float] = []
    for line in lines:
        for word in line.words or []:
            if sum(char.isalnum() for char in word.text) < 2:
                continue
            confidences.append(word.confidence)
            if len(word.text) < 3:
                continue
            box = word.box
            y0, y1 = int(box.y * height), int((box.y + box.h) * height) + 1
            x0, x1 = int(box.x * width), int((box.x + box.w) * width) + 1
            crop = gray[y0:y1, x0:x1]
            if crop.size >= 20:
                contrasts.append(float(np.percentile(crop, 95) - np.percentile(crop, 3)))
    stats: dict[str, float] = {}
    if contrasts:
        stats["text_contrast"] = round(float(np.median(contrasts)), 1)
    if confidences:
        weak = sum(value < WEAK_WORD for value in confidences) / len(confidences)
        stats["weak_words"] = round(weak, 3)
    return stats


def advise(quality: dict[str, float | str | bool]) -> list[str]:
    """Советы по сведениям о снимке. У текстового слоя PDF советов нет."""
    if quality.get("pdf_text") or "sharpness" not in quality:
        return []
    tips: list[str] = []
    if float(quality.get("upscale", 1.0)) >= LOW_RESOLUTION_UPSCALE:
        tips.append(LOW_RESOLUTION)
    elif float(quality["sharpness"]) < BLUR_SHARPNESS:
        # У мелкого снимка резкость падает от увеличения: про смаз тогда не говорим.
        tips.append(BLURRY)
    if float(quality.get("uneven_light", 0.0)) >= UNEVEN_LIGHT:
        tips.append(SHADOW)
    if not tips and float(quality.get("text_contrast", 255.0)) < FADED_CONTRAST:
        tips.append(GLARE)
    if abs(float(quality.get("skew_degrees", 0.0))) >= STRONG_SKEW:
        tips.append(TILTED)
    if not tips and float(quality.get("weak_words", 0.0)) >= WEAK_SHARE:
        tips.append(WEAK_TEXT)
    return tips
