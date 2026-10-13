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
from pathlib import Path

import yaml

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


def load_hints(path: Path) -> dict[str, list[str]]:
    """Читает фразы, которыми студенты спрашивают о пунктах Положения."""
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        str(number): [str(phrase) for phrase in phrases or []] for number, phrases in raw.items()
    }


class RuleIndex:
    def __init__(self, rulebook: RuleBook, hints: dict[str, list[str]] | None = None):
        self.points = list(rulebook)
        self.hints: list[tuple[frozenset[str], RulePoint]] = []
        for number, phrases in (hints or {}).items():
            if number not in rulebook:
                raise ValueError(f"rules_hints: в Положении нет пункта {number}")
            for phrase in phrases:
                wanted = frozenset(stems(phrase))
                # Фраза из одного значимого слова («отпуск») подошла бы к любому вопросу.
                if len(wanted) < 2:
                    raise ValueError(f"rules_hints: фраза «{phrase}» слишком короткая")
                self.hints.append((wanted, rulebook.get(number)))
        self.terms = [set(stems(f"{point.section} {point.text}")) for point in self.points]
        counts: dict[str, int] = {}
        for terms in self.terms:
            for term in terms:
                counts[term] = counts.get(term, 0) + 1
        total = len(self.points)
        self.idf = {term: math.log(1 + total / count) for term, count in counts.items()}
        self.vocabulary = frozenset(counts)
        self.hint_vocabulary = self.vocabulary | {
            term for wanted, _ in self.hints for term in wanted
        }

    def search(self, question: str, prefer_section: str | None = None) -> list[Match]:
        """Пункты, покрывающие вопрос, от лучшего к худшему. Пустой список — ответа нет."""
        asked = set(stems(question)) - _NEUTRAL
        if not asked:
            return []
        hinted = self._by_hint(asked)
        if hinted is not None:
            return [hinted]
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

    def _by_hint(self, asked: set[str]) -> Match | None:
        """Пункт, к которому привязана фраза из вопроса.

        Все слова фразы должны быть в вопросе. Посторонних слов, которых нет ни в
        Положении, ни в подсказках, допускается не больше одного: иначе вопрос,
        скорее всего, о другом.
        """
        foreign = len(asked - self.hint_vocabulary)
        best: tuple[float, RulePoint] | None = None
        tie = False
        for wanted, point in self.hints:
            if not wanted <= asked or foreign > 1:
                continue
            score = len(wanted) - 0.15 * len(asked - wanted)
            if best is None or score > best[0]:
                best, tie = (score, point), False
            elif score == best[0] and point.number != best[1].number:
                tie = True
        if best is None or tie:
            return None
        return Match(best[1], 1.0)
