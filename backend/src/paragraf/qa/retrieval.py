"""Поиск пункта Положения, который отвечает на вопрос.

Используется обычный лексический поиск: слова вопроса и пунктов приводятся к
основам, редкие слова весят больше частых. Главное требование — не отвечать
наугад. Если в вопросе есть значимое слово, которого нет нигде в Положении
(«стипендия», «телефон», «кабинет»), значит вопрос о том, чего Положение не
описывает, и поиск возвращает пустой результат.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from paragraf.qa.lexicon import stems
from paragraf.rules.kb import RuleBook, RulePoint

# Слова вопроса, которые не называют тему и могут отсутствовать в Положении.
_NEUTRAL = frozenset(
    stems(
        "нужен нужна нужно нужны требуется требуются должен должна должно должны обязателен "
        "обязательна обязательно обязательны можно нельзя надо ли бывает считается значит "
        "положение положению правила правилам пункт сервис система проверяет проверяется "
        "проверка скажи расскажи объясни такое означает вообще ваш ваши вы меня мой документ "
        "может могут могу умеет входит входят",
        keep_stopwords=True,
    )
)

MIN_COVERAGE = 0.6
MIN_MARGIN = 0.05


@dataclass
class Match:
    point: RulePoint
    score: float


class RuleIndex:
    def __init__(self, rulebook: RuleBook):
        self.points = list(rulebook)
        self.terms = [set(stems(f"{point.section} {point.text}")) for point in self.points]
        counts: dict[str, int] = {}
        for terms in self.terms:
            for term in terms:
                counts[term] = counts.get(term, 0) + 1
        total = len(self.points)
        self.idf = {term: math.log(1 + total / count) for term, count in counts.items()}
        self.vocabulary = frozenset(counts)

    def search(self, question: str, prefer_section: str | None = None) -> list[Match]:
        """Пункты, покрывающие вопрос, от лучшего к худшему. Пустой список — ответа нет."""
        asked = set(stems(question)) - _NEUTRAL
        if not asked:
            return []
        if asked - self.vocabulary:
            return []
        weight = sum(self.idf[term] for term in asked)
        ranked: list[Match] = []
        for point, terms in zip(self.points, self.terms, strict=True):
            common = asked & terms
            if not common:
                continue
            score = sum(self.idf[term] for term in common) / weight
            if prefer_section and point.number.split(".")[0] == prefer_section:
                score *= 1.12
            ranked.append(Match(point, score))
        ranked.sort(key=lambda match: -match.score)
        if not ranked or ranked[0].score < MIN_COVERAGE:
            return []
        best = ranked[0]
        return [match for match in ranked[:2] if best.score - match.score <= MIN_MARGIN]
