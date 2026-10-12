"""Разбор русского вопроса на значимые основы слов."""

from __future__ import annotations

import re
from functools import lru_cache

import snowballstemmer

_stemmer = snowballstemmer.stemmer("russian")

# Слова, которые есть почти в любом вопросе и ничего не говорят о его теме.
STOPWORDS = frozenset(
    """
    а в во и или к ко на о об от по с со у за из для до не ни же ли бы то это этот эта эти
    что как какой какая какое какие каков какова каково каковы кто чей чья где когда куда
    сколько почему зачем мне мой моя мое мои я мы вы он она они его ее их нам вам
    есть быть был была было были будет можно нужно надо ли пожалуйста укажи укажите назови
    назовите скажи скажите подскажи подскажите напиши напишите значение значения поле поля
    полей данный данная данном указан указана указано указаны написано написан
    стоит такой такая там тут здесь
    """.split()
)


def tokens(text: str) -> list[str]:
    """Слова вопроса в нижнем регистре, «ё» заменена на «е»."""
    return re.findall(r"[a-zа-я0-9]+", text.casefold().replace("ё", "е"))


@lru_cache(maxsize=8192)
def stem(word: str) -> str:
    return _stemmer.stemWord(word)


def stems(text: str, keep_stopwords: bool = False) -> list[str]:
    """Основы значимых слов. Числа и служебные слова отбрасываются."""
    out = []
    for token in tokens(text):
        if not keep_stopwords and token in STOPWORDS:
            continue
        if token.isdigit():
            continue
        out.append(stem(token))
    return out
