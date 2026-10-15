"""Автоопределение типа документа по распознанному тексту."""

from __future__ import annotations

from rapidfuzz import fuzz

from docrux import textnorm
from docrux.doctypes import DocType, DocTypeRegistry
from docrux.extraction import freeform
from docrux.extraction.fields import locate
from docrux.models import Line

MIN_SCORE = 0.3
MIN_MARGIN = 0.07


def score_type(doc_type: DocType, lines: list[Line]) -> float:
    """Оценка от 0 до 1: насколько текст похож на документ этого типа."""
    keys = [textnorm.match_key(line.text) for line in lines]
    text = " ".join(keys)

    title = 0.0
    for wanted in doc_type.detect.titles:
        wanted_key = textnorm.match_key(wanted)
        title = max(title, *(fuzz.ratio(wanted_key, key) / 100 for key in keys), 0.0)
        title = max(title, fuzz.partial_ratio(wanted_key, text) / 100 * 0.9)

    keywords = doc_type.detect.keywords
    hits = sum(fuzz.partial_ratio(textnorm.match_key(word), text) >= 88 for word in keywords)
    keyword_share = hits / len(keywords) if keywords else 0.0

    # Считаем и поля с метками, и то, что нашлось в свободном тексте по образцам фраз.
    located = {key for key in locate(doc_type, lines) if "+" not in key}
    text_fields = [field for field in doc_type.fields if not field.is_mark]
    loose = freeform.find(doc_type, lines, {field.key for field in text_fields} - located)
    share = min(1.0, (len(located) + 0.8 * len(loose)) / max(1, len(text_fields)))

    return 0.45 * (title if title >= 0.8 else 0.0) + 0.2 * keyword_share + 0.35 * share


def detect_type(registry: DocTypeRegistry, lines: list[Line]) -> tuple[DocType | None, float]:
    """Возвращает самый подходящий тип и уверенность.

    Если ни один тип не набрал достаточной оценки, возвращается None: в этом
    случае тип должен выбрать пользователь.
    """
    ranked = sorted(
        ((score_type(doc_type, lines), doc_type) for doc_type in registry),
        key=lambda item: -item[0],
    )
    if not ranked:
        return None, 0.0
    best_score, best = ranked[0]
    runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
    if best_score < MIN_SCORE or best_score - runner_up < MIN_MARGIN:
        return None, best_score
    return best, best_score
