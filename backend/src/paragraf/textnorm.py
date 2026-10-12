"""Нормализация текста и значений полей.

Здесь собрано всё, что превращает «сырую» строку после OCR в значение карточки:
чистка пробелов и кавычек, разбор дат, починка букв и цифр, которые OCR путает.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

NOT_FOUND = "не найдено"

_MONTHS = {
    "январ": 1,
    "феврал": 2,
    "март": 3,
    "апрел": 4,
    "мая": 5,
    "май": 5,
    "мае": 5,
    "июн": 6,
    "июл": 7,
    "август": 8,
    "сентябр": 9,
    "октябр": 10,
    "ноябр": 11,
    "декабр": 12,
}

# Латинские буквы, которые выглядят как кириллические, и наоборот.
_LAT_TO_CYR = str.maketrans(
    "ABCEHKMOPTXYaceopxy",
    "АВСЕНКМОРТХУасеорху",
)
# Буквы, которые OCR ставит на место цифр.
_LETTER_TO_DIGIT = str.maketrans({"О": "0", "о": "0", "O": "0", "o": "0", "З": "3", "з": "3",
                                  "l": "1", "I": "1", "|": "1", "Б": "6", "б": "6", "S": "5"})
_DIGIT_TO_LETTER = str.maketrans({"0": "О", "3": "З", "6": "Б"})

_PLACEHOLDER = re.compile(r"^[\s_\-–—.·…]*$")
_QUOTES = "«»“”„\""


def squash(text: str) -> str:
    """Схлопывает пробелы и приводит Unicode к NFC."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def compare_key(text: str) -> str:
    """Ключ сравнения, совпадающий с нормализацией автопроверки."""
    value = unicodedata.normalize("NFC", text).casefold().replace("ё", "е")
    for char in "«»“”„":
        value = value.replace(char, '"')
    return re.sub(r"\s+", " ", value).strip()


def match_key(text: str) -> str:
    """Грубый ключ для нечёткого сравнения меток: только буквы и цифры."""
    value = compare_key(text).translate(_LAT_TO_CYR)
    return re.sub(r"[^0-9a-zа-я]+", " ", value).strip()


def is_blank(value: str | None) -> bool:
    """Пустое значение: ничего нет или стоит только линия для заполнения."""
    return value is None or bool(_PLACEHOLDER.match(value))


def strip_placeholder(value: str) -> str:
    """Убирает линию-прочерк, оставшуюся от незаполненной части строки."""
    value = re.sub(r"_{2,}", " ", value)
    return squash(value).strip(" .:;,")


def fix_quotes(value: str) -> str:
    """Парные «ёлочки» вместо любых кавычек, которые выдал OCR."""
    value = re.sub(r"[<‹]{2}|,,", "«", value)
    value = re.sub(r"[>›]{2}|''", "»", value)
    out: list[str] = []
    opened = False
    for char in value:
        if char in _QUOTES:
            if char == "«":
                opened = True
            elif char == "»":
                opened = False
            elif char in "“„":
                char, opened = "«", True
            elif char == "”":
                char, opened = "»", False
            else:
                char = "»" if opened else "«"
                opened = not opened
        out.append(char)
    return "".join(out)


def to_cyrillic(value: str) -> str:
    """Заменяет латинские двойники кириллическими буквами."""
    return value.translate(_LAT_TO_CYR)


def _digits(token: str) -> str:
    return token.translate(_LETTER_TO_DIGIT)


def parse_date(raw: str) -> str | None:
    """Приводит дату к ГГГГ-ММ-ДД. Понимает 01.09.2026 и «1 сентября 2026 года»."""
    text = squash(raw).casefold().replace("ё", "е")
    if not text:
        return None

    iso = re.search(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)", text)
    if iso:
        return _build(int(iso[1]), int(iso[2]), int(iso[3]))

    numeric = re.search(
        r"(?<![\w])([0-9оoзl|i]{1,2})\s*[.,/\-]\s*([0-9оoзl|i]{1,2})\s*[.,/\-]\s*([0-9оoзl|i]{4}|[0-9оoзl|i]{2})(?![\w])",
        text,
    )
    if numeric:
        day, month, year = (int(_digits(part)) for part in numeric.groups())
        if year < 100:
            year += 2000
        return _build(year, month, day)

    worded = re.search(r"([0-9оoзl|i]{1,2})\s*[\"«»]?\s*([а-я]{3,})\.?\s*([0-9оoзl|i]{4})", text)
    if worded:
        month = _month(worded[2])
        if month:
            return _build(int(_digits(worded[3])), month, int(_digits(worded[1])))
    return None


def find_dates(raw: str) -> list[str]:
    """Все даты в строке по порядку появления."""
    text = squash(raw)
    pattern = re.compile(
        r"\d{4}-\d{1,2}-\d{1,2}"
        r"|\d{1,2}\s*[./]\s*\d{1,2}\s*[./]\s*\d{2,4}"
        r"|\d{1,2}\s*[\"«»]?\s*[А-Яа-яёЁ]{3,}\.?\s*\d{4}"
    )
    found = []
    for chunk in pattern.findall(text):
        parsed = parse_date(chunk)
        if parsed:
            found.append(parsed)
    return found


def _month(word: str) -> int | None:
    for stem, number in _MONTHS.items():
        if word.startswith(stem):
            return number
    # OCR мог ошибиться в одной букве: берём ближайшее название месяца.
    from rapidfuzz import fuzz, process

    names = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
             "сентября", "октября", "ноября", "декабря"]
    best = process.extractOne(word, names, scorer=fuzz.ratio)
    if best and best[1] >= 75:
        return names.index(best[0]) + 1
    return None


def _build(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def parse_integer(raw: str) -> str | None:
    """Целое число строкой: «3», «3 курс», «III»."""
    text = squash(raw)
    match = re.search(r"\d+", _digits(text) if len(text) <= 3 else text)
    if match:
        return str(int(match[0]))
    roman = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6}
    return str(roman[text.casefold()]) if text.casefold() in roman else None


def clean_code(raw: str) -> str:
    """Номера и шифры групп: «ОБ-1001», «ИВТ-23-4».

    Внутри одного кода буквы приводятся к кириллице, а в цифровых частях
    исправляются буквы, похожие на цифры.
    """
    text = squash(raw).lstrip("№# ").replace("—", "-").replace("–", "-")
    text = re.sub(r"\s*-\s*", "-", text)
    parts = []
    for part in text.split("-"):
        digits = sum(char.isdigit() for char in part)
        letters = sum(char.isalpha() for char in part)
        if digits > letters:
            part = _digits(part)
        elif letters > digits:
            part = to_cyrillic(part).translate(_DIGIT_TO_LETTER).upper()
        parts.append(part)
    return "-".join(parts)


def clean_person(raw: str) -> str:
    """ФИО: кириллица, одна заглавная буква в начале каждого слова сохраняется как есть."""
    text = to_cyrillic(squash(raw)).translate(_DIGIT_TO_LETTER)
    text = re.sub(r"[^А-Яа-яЁё\-\s.]", "", text)
    return squash(text)


def clean_text(raw: str) -> str:
    """Обычное текстовое значение."""
    return fix_quotes(squash(raw))
