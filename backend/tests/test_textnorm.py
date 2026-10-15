import pytest

from docrux import textnorm


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("01.09.2026", "2026-09-01"),
        ("1 сентября 2026 года", "2026-09-01"),
        ("31 августа 2027 г.", "2027-08-31"),
        ("7 октября 2026", "2026-10-07"),
        ("2026-07-18", "2026-07-18"),
        ("15/07/2026", "2026-07-15"),
        ("«18» июля 2026 года", "2026-07-18"),
        ("О1.О9.2О26", "2026-09-01"),
        ("1 сентабря 2026 года", "2026-09-01"),
        ("1 мая 2026 года", "2026-05-01"),
    ],
)
def test_parse_date(raw, expected):
    assert textnorm.parse_date(raw) == expected


@pytest.mark.parametrize("raw", ["", "____", "31.02.2026", "вчера", "32 января 2026 года"])
def test_parse_date_rejects_garbage(raw):
    assert textnorm.parse_date(raw) is None


@pytest.mark.parametrize("raw", ["", "   ", "________________", "_ _ _", "—", "..."])
def test_blank_values(raw):
    assert textnorm.is_blank(raw)


def test_filled_value_is_not_blank():
    assert not textnorm.is_blank("очная")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ОБ-1001", "ОБ-1001"),
        ("OБ-1001", "ОБ-1001"),  # латинская O
        ("ОБ-1ОО1", "ОБ-1001"),  # буквы О вместо нулей
        ("ОБ­6305", "ОБ-6305"),  # мягкий перенос вместо дефиса
        ("№ ПР-2021", "ПР-2021"),
        ("ИВТ - 23 - 4", "ИВТ-23-4"),
        ("ЖР-25-1", "ЖР-25-1"),
        ("БЩ-24-7", "БЩ-24-7"),
        ("ЗО-20-3", "ЗО-20-3"),
    ],
)
def test_clean_code(raw, expected):
    assert textnorm.clean_code(raw) == expected


def test_clean_person_keeps_yo_and_hyphen():
    assert (
        textnorm.clean_person("Салтыков-Щедрин  Артём Фёдорович")
        == "Салтыков-Щедрин Артём Фёдорович"
    )


def test_clean_person_replaces_latin_lookalikes():
    assert textnorm.clean_person("Cоколов Oлег") == "Соколов Олег"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('Учебный университет "Меридиан"', "Учебный университет «Меридиан»"),
        ("Учебный университет «Меридиан»", "Учебный университет «Меридиан»"),
        ("Учебная академия “Горизонт”", "Учебная академия «Горизонт»"),
        ("Учебный институт <<Вектор>>", "Учебный институт «Вектор»"),
    ],
)
def test_fix_quotes(raw, expected):
    assert textnorm.fix_quotes(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"), [("3", "3"), ("3 курс", "3"), ("II", "2"), ("З", "3")]
)
def test_parse_integer(raw, expected):
    assert textnorm.parse_integer(raw) == expected


def test_compare_key_matches_evaluator_rules():
    assert textnorm.compare_key("  Артём   «ЁЖ» ") == 'артем "еж"'
