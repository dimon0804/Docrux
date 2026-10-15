from __future__ import annotations

import numpy as np
import pytest

from docrux.imaging import advice
from docrux.models import Box, Line, Word

# Так выглядят сведения о чистом скане открытого набора.
CLEAN = {
    "page_cropped": False,
    "skew_degrees": 0.0,
    "upscale": 1.5,
    "sharpness": 290.0,
    "uneven_light": 0.0,
    "light_corrected": False,
    "text_contrast": 231.0,
    "weak_words": 0.02,
    "file_kind": "png",
    "pages": 1,
}


def test_clean_scan_gets_no_advice():
    assert advice.advise(CLEAN) == []


def test_pdf_text_layer_gets_no_advice():
    assert advice.advise({"pdf_text": True, "file_kind": "pdf", "pages": 1}) == []


@pytest.mark.parametrize(
    ("change", "tip"),
    [
        ({"sharpness": 20.0}, advice.BLURRY),
        ({"upscale": 2.7, "sharpness": 45.0}, advice.LOW_RESOLUTION),
        ({"uneven_light": 0.4, "light_corrected": True}, advice.SHADOW),
        ({"text_contrast": 120.0}, advice.GLARE),
        ({"skew_degrees": -12.0}, advice.TILTED),
        ({"weak_words": 0.2}, advice.WEAK_TEXT),
    ],
)
def test_each_problem_gets_its_tip(change, tip):
    assert advice.advise(CLEAN | change) == [tip]


def test_thresholds_are_edges():
    assert advice.advise(CLEAN | {"sharpness": advice.BLUR_SHARPNESS}) == []
    assert advice.advise(CLEAN | {"uneven_light": advice.UNEVEN_LIGHT - 0.01}) == []
    assert advice.advise(CLEAN | {"upscale": advice.LOW_RESOLUTION_UPSCALE - 0.01}) == []
    assert advice.advise(CLEAN | {"skew_degrees": 1.5}) == []


def test_small_photo_is_not_called_blurry():
    # Резкость упала от увеличения мелкого снимка: совет один, про разрешение.
    tips = advice.advise(CLEAN | {"upscale": 2.9, "sharpness": 15.0})
    assert tips == [advice.LOW_RESOLUTION]


def test_blur_alone_is_not_called_glare():
    # Смаз тоже снижает контраст слов, но причина в нём, а не в блике.
    tips = advice.advise(CLEAN | {"sharpness": 20.0, "text_contrast": 130.0})
    assert tips == [advice.BLURRY]
    assert advice.advise(CLEAN | {"text_contrast": advice.FADED_CONTRAST}) == []


def test_weak_text_tip_only_when_nothing_else_explains_it():
    tips = advice.advise(CLEAN | {"sharpness": 20.0, "weak_words": 0.3})
    assert tips == [advice.BLURRY]


def test_text_stats_measure_contrast_and_confidence():
    gray = np.full((100, 200), 255, np.uint8)
    gray[20:40, 20:80] = 30
    gray[60:80, 20:80] = 180
    box = Box(x=0.05, y=0.15, w=0.4, h=0.3)
    lines = [
        Line(text="текст", box=box, words=[Word(text="текст", box=box, confidence=0.95)]),
        Line(
            text="бледный",
            box=box,
            words=[Word(text="бледный", box=Box(x=0.05, y=0.55, w=0.4, h=0.3), confidence=0.4)],
        ),
    ]
    stats = advice.text_stats(gray, lines)
    assert stats["weak_words"] == 0.5
    # Контраст тёмного слова 225, бледного 75: середина между ними.
    assert stats["text_contrast"] == 150.0
