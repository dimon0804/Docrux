"""Ответы на свободные вопросы с помощью небольшой локальной языковой модели.

Модель работает на этой же машине через сервер llama.cpp, внешние API не
используются. К ней обращаются только тогда, когда обычный разбор вопроса
ничего не нашёл: человек спросил другими словами, чем написано в Положении.

Модели запрещено отвечать от себя. Она обязана вернуть дословную цитату из
документа или из пункта Положения, и сервис проверяет, что такая цитата там
действительно есть. Если цитаты нет или она не найдена, ответ отбрасывается и
студент получает честное «информации нет».
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from rapidfuzz import fuzz

from paragraf import textnorm
from paragraf.models import Analysis
from paragraf.rules.kb import RuleBook

SYSTEM = """Ты помощник деканата. Отвечай на вопрос студента строго по двум источникам:
ПОЛОЖЕНИЕ и ДОКУМЕНТ. Больше ты ничего не знаешь.

Правила:
1. Если ответ есть в Положении, укажи source = "rules", номер пункта в rule и дословную цитату из этого пункта в quote.
2. Если ответ есть в документе, укажи source = "document" и дословную цитату из документа в quote.
3. Если ни в Положении, ни в документе ответа нет, верни answerable = false. Не додумывай и не используй общие знания: про стоимость, стипендии, сроки, телефоны, адреса, расписание, общежитие в источниках ничего нет.
4. Если Положение прямо говорит, что что-то не установлено или не проверяется, это тоже ответ: процитируй этот пункт.
5. Отвечай по-русски, одним-двумя предложениями, без вступлений.

ПОЛОЖЕНИЕ
{rules}"""

SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "source": {"type": "string", "enum": ["rules", "document", "none"]},
        "rule": {"type": "string"},
        "quote": {"type": "string"},
        "answer": {"type": "string"},
    },
    "required": ["answerable", "source", "rule", "quote", "answer"],
}

MAX_DOCUMENT_CHARS = 3500
MIN_QUOTE = 10
QUOTE_MATCH = 88


@dataclass
class Grounded:
    answer: str
    sources: list[str]
    quote: str


class LocalLLM:
    def __init__(self, url: str, rulebook: RuleBook, timeout: float = 90.0):
        self.url = url.rstrip("/")
        self.rulebook = rulebook
        self.timeout = timeout
        rules = "\n".join(f"{point.number}. {point.text}" for point in rulebook)
        self.system = SYSTEM.format(rules=rules)

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.url}/health", timeout=2) as response:  # noqa: S310
                return response.status == 200
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def answer(self, analysis: Analysis, question: str) -> Grounded | None:
        """Ответ, подтверждённый цитатой, или None, если его нет либо модель недоступна."""
        document = self._document(analysis)
        payload = {
            "messages": [
                {"role": "system", "content": self.system},
                {"role": "user", "content": f"ДОКУМЕНТ\n{document}\n\nВОПРОС\n{question}"},
            ],
            "temperature": 0,
            "max_tokens": 260,
            "cache_prompt": True,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer", "strict": True, "schema": SCHEMA},
            },
        }
        request = urllib.request.Request(  # noqa: S310
            f"{self.url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                body = json.loads(response.read().decode("utf-8"))
            reply = json.loads(body["choices"][0]["message"]["content"])
        except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError, TypeError):
            return None
        return self._verify(reply, analysis, document)

    def _document(self, analysis: Analysis) -> str:
        lines = [f"Тип: {analysis.document_title}"]
        for field in analysis.fields:
            if field.type == "mark":
                lines.append(f"{field.label}: {'есть' if field.found else 'нет'}")
            elif field.found:
                lines.append(f"{field.label}: {field.value}")
            else:
                lines.append(f"{field.label}: не найдено")
        if analysis.text:
            lines.append("Текст документа:")
            lines.append(analysis.text[:MAX_DOCUMENT_CHARS])
        return "\n".join(lines)

    def _verify(self, reply: dict, analysis: Analysis, document: str) -> Grounded | None:
        """Принимает ответ, только если цитата действительно стоит в названном источнике."""
        if not isinstance(reply, dict) or reply.get("answerable") is not True:
            return None
        answer = textnorm.squash(str(reply.get("answer", "")))
        quote = textnorm.squash(str(reply.get("quote", "")))
        if not answer or len(quote) < MIN_QUOTE:
            return None
        source = reply.get("source")
        if source == "rules":
            number = str(reply.get("rule", "")).strip().rstrip(".")
            if number not in self.rulebook:
                number = self._find_rule(quote) or ""
            if number and _contains(self.rulebook.get(number).text, quote):
                return Grounded(answer, [f"rule:{number}"], quote)
            return None
        if source == "document":
            for field in analysis.fields:
                if field.found and isinstance(field.value, str) and _contains(field.value, quote):
                    return Grounded(answer, [f"field:{field.key}"], quote)
            if _contains(document, quote):
                return Grounded(answer, ["text"], quote)
        return None

    def _find_rule(self, quote: str) -> str | None:
        for point in self.rulebook:
            if _contains(point.text, quote):
                return point.number
        return None


def _contains(text: str, quote: str) -> bool:
    """Стоит ли цитата в тексте. Допускаются мелкие расхождения, но не выдумка."""
    haystack, needle = textnorm.compare_key(text), textnorm.compare_key(quote)
    # Цитата не может быть длиннее источника: иначе совпадением считался бы любой обрывок.
    if not needle or len(needle) > len(haystack):
        return False
    return needle in haystack or fuzz.partial_ratio(needle, haystack) >= QUOTE_MATCH
