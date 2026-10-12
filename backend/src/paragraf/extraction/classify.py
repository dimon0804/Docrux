"""Автоопределение типа документа по распознанному тексту."""

from __future__ import annotations

from rapidfuzz import fuzz

from paragraf import textnorm
from paragraf.doctypes import DocType, DocTypeRegistry
from paragraf.extraction.fields import locate
from paragraf.models import Line


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
    hits = sum(
        fuzz.partial_ratio(textnorm.match_key(word), text) >= 88 for word in keywords
    )
    keyword_share = hits / len(keywords) if keywords else 0.0

    located = locate(doc_type, lines)
    label_share = len(located) / max(1, len(doc_type.fields) + len(doc_type.composites) * 0)
    label_share = min(1.0, label_share)

    return 0.5 * (title if title >= 0.8 else 0.0) + 0.2 * keyword_share + 0.3 * label_share


def detect_type(registry: DocTypeRegistry, lines: list[Line]) -> tuple[DocType | None, float]:
    """Возвращает самый подходящий тип и уверенность.

    Если ни один тип не набрал достаточной оценки, возвращается None: в этом
    случае тип должен выбрать пользователь.
    """
    ranked = sorted(((score_type(doc_type, lines), doc_type) for doc_type in registry),
                    key=lambda item: -item[0])
    if not ranked:
        return None, 0.0
    best_score, best = ranked[0]
    runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
    if best_score < 0.35 or best_score - runner_up < 0.08:
        return None, best_score
    return best, best_score
