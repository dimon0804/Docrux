"""Генератор учебных документов для проверки сервиса.

Собирает набор в том же формате, что и пакет организаторов: PDF и PNG каждого
документа, documents.json, questions.json и reference_results.json. Значения
полей берутся из широких словарей, чтобы проверить распознавание на именах и
шифрах, которых нет в открытом наборе.

    python tools/synth.py --out data/synth --count 60 --seed 7
"""

from __future__ import annotations

import argparse
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

import pymupdf

PAGE_W, PAGE_H = 595.2756, 841.8898
PNG_WIDTH = 1132
MONTHS = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]

SURNAMES_M = """Александров Мельников Жуков Климов Соколов Орлов Крылов Морозов Петров Захаров
Павлов Иванов Романов Данилов Шестаков Семенов Смирнов Волков Щербаков Ёлкин Журавлёв
Подъячев Цыганков Хрущёв Фёдоров Юрьев Яковлев Эйхман Чижов Шишкин Гущин Зайцев Быстров
Воробьёв Григорьев Дьячков Ежов Жданов Ильин Кудрявцев Лебедев Мухаметшин Нуриев Объедков
Прокофьев Рябцев Субботин Тимофеев Уткин Филиппов Харитонов Царёв Чернышёв Шульгин
Мамин-Сибиряк Римский-Корсаков Салтыков-Щедрин""".split()
NAMES_M = """Артём Денис Андрей Борис Олег Максим Фёдор Юрий Роман Илья Виктор Глеб Кирилл
Никита Лев Семён Пётр Савелий Матвей Эдуард Ярослав Тимофей Георгий Вячеслав Зиновий""".split()
PATRONYMS_M = """Игоревич Дмитриевич Николаевич Сергеевич Викторович Алексеевич Михайлович
Андреевич Фёдорович Юрьевич Семёнович Петрович Эдуардович Яковлевич Геннадьевич
Вячеславович Ильич Саввич""".split()
SURNAMES_F = """Ильина Соколова Кузнецова Щербакова Журавлёва Фёдорова Яковлева Чижова Гущина
Зайцева Воробьёва Лебедева Субботина Харитонова Царёва Шульгина Объедкова""".split()
NAMES_F = """Елена Анна Мария Ольга Юлия Наталья Ксения Алёна Жанна Эльвира Любовь Софья
Таисия Ульяна Фаина Зинаида""".split()
PATRONYMS_F = """Андреевна Викторовна Сергеевна Фёдоровна Юрьевна Семёновна Петровна
Эдуардовна Яковлевна Геннадьевна Ильинична Саввична""".split()

UNIVERSITIES = [
    "Учебный университет «Меридиан»",
    "Учебная академия «Горизонт»",
    "Учебный институт «Вектор»",
    "Учебный университет «Созвездие»",
    "Учебная академия «Южный берег»",
    "Учебный институт «Эхо»",
]
PROGRAMS = [
    "38.03.01 Экономика",
    "09.03.01 Информатика и вычислительная техника",
    "42.03.02 Журналистика",
    "40.03.01 Юриспруденция",
    "01.03.02 Прикладная математика",
    "44.03.05 Педагогическое образование",
    "09.03.04 Программная инженерия",
    "27.03.04 Управление в технических системах",
]
STUDY_FORMS = ["очная", "заочная", "очно-заочная"]
GROUP_PREFIXES = ["ЖР", "ЭК", "ИВТ", "ЮР", "ПМ", "ПИ", "УТС", "ФЛ", "ХМ", "БЩ"]
REASONS = [
    "по состоянию здоровья",
    "по семейным обстоятельствам",
    "в связи с уходом за родственником",
    "в связи с призывом на военную службу",
    "в связи с рождением ребёнка",
]
ORGANIZATIONS = [
    "Учебная организация «Спектр»",
    "Учебная организация «Орбита»",
    "Учебная организация «Парус»",
    "Учебная организация «Жёлтый клён»",
    "Учебная организация «Щит и перо»",
]
GRADES = ["отлично", "хорошо", "удовлетворительно", "зачтено"]

UNANSWERABLE = [
    "Какова стоимость обучения за следующий семестр?",
    "Какой размер стипендии положен студенту?",
    "Какой срок рассмотрения документа деканатом?",
    "По какому номеру телефона можно связаться с деканатом?",
    "В каком кабинете принимают оригиналы документов?",
]

TYPES = {
    "study_certificate": {
        "left": 48,
        "subtitle": "Учебный документооборот / отдел сопровождения студентов",
        "title": "СПРАВКА ОБ ОБУЧЕНИИ",
        "intro": "Сведения об обучении студента приведены ниже.",
        "fields": [
            ("student_name", "ФИО студента"),
            ("university", "Название вуза"),
            ("program", "Направление подготовки"),
            ("study_form", "Форма обучения"),
            ("study_start", "Начало периода обучения"),
            ("study_end", "Окончание периода обучения"),
            ("document_number", "Номер справки"),
            ("issue_date", "Дата выдачи"),
        ],
        "signature": "Подпись сотрудника",
        "seal": True,
        "rules": {"text": "3.1", "signature_present": "3.2", "seal_present": "3.3"},
    },
    "academic_leave_application": {
        "left": 56,
        "subtitle": "В деканат учебного университета «Меридиан»",
        "title": "ЗАЯВЛЕНИЕ НА АКАДЕМИЧЕСКИЙ ОТПУСК",
        "intro": "Прошу предоставить академический отпуск на указанный период.",
        "fields": [
            ("student_name", "ФИО студента"),
            ("group", "Учебная группа"),
            ("course", "Курс"),
            ("leave_reason", "Причина отпуска"),
            ("leave_start", "Дата начала отпуска"),
            ("leave_end", "Дата окончания отпуска"),
            ("application_date", "Дата заявления"),
        ],
        "signature": "Подпись студента",
        "seal": False,
        "rules": {"text": "4.1", "signature_present": "4.2"},
    },
    "internship_certificate": {
        "left": 56,
        "subtitle": "Учебный документооборот / отдел сопровождения студентов",
        "title": "СПРАВКА О ПРАКТИКЕ",
        "intro": "Сведения о прохождении практики приведены ниже.",
        "fields": [
            ("student_name", "ФИО студента"),
            ("organization", "Название организации"),
            ("internship_start", "Дата начала практики"),
            ("internship_end", "Дата окончания практики"),
            ("supervisor_name", "ФИО руководителя практики"),
            ("grade", "Оценка"),
            ("document_number", "Номер справки"),
            ("issue_date", "Дата выдачи"),
        ],
        "signature": "Подпись руководителя",
        "seal": True,
        "rules": {"text": "5.1", "signature_present": "5.2", "seal_present": "5.3"},
    },
}
DATE_KEYS = {
    "study_start",
    "study_end",
    "issue_date",
    "leave_start",
    "leave_end",
    "application_date",
    "internship_start",
    "internship_end",
}


def person(rng: random.Random, female: bool = False) -> str:
    if female:
        return f"{rng.choice(SURNAMES_F)} {rng.choice(NAMES_F)} {rng.choice(PATRONYMS_F)}"
    return f"{rng.choice(SURNAMES_M)} {rng.choice(NAMES_M)} {rng.choice(PATRONYMS_M)}"


def values(doc_type: str, rng: random.Random, number: int) -> dict[str, str]:
    """Значения полей в нормализованном виде: даты в ISO."""
    day = lambda start, spread: (start + timedelta(days=rng.randrange(spread))).isoformat()  # noqa: E731
    if doc_type == "study_certificate":
        start_year = rng.choice([2021, 2022, 2023, 2024])
        return {
            "student_name": person(rng),
            "university": rng.choice(UNIVERSITIES),
            "program": rng.choice(PROGRAMS),
            "study_form": rng.choice(STUDY_FORMS),
            "study_start": f"{start_year}-09-01",
            "study_end": day(date(2026, 6, 1), 120),
            "document_number": f"ОБ-{number}",
            "issue_date": day(date(2026, 9, 1), 60),
        }
    if doc_type == "academic_leave_application":
        return {
            "student_name": person(rng),
            "group": f"{rng.choice(GROUP_PREFIXES)}-{rng.randint(20, 26)}-{rng.randint(1, 9)}",
            "course": str(rng.randint(1, 5)),
            "leave_reason": rng.choice(REASONS),
            "leave_start": day(date(2026, 10, 20), 60),
            "leave_end": day(date(2027, 6, 1), 120),
            "application_date": day(date(2026, 9, 20), 28),
        }
    return {
        "student_name": person(rng),
        "organization": rng.choice(ORGANIZATIONS),
        "internship_start": day(date(2026, 5, 20), 30),
        "internship_end": day(date(2026, 7, 1), 30),
        "supervisor_name": person(rng, female=rng.random() < 0.7),
        "grade": rng.choice(GRADES),
        "document_number": f"ПР-{number}",
        "issue_date": day(date(2026, 7, 16), 30),
    }


def shown(key: str, value: str, worded: bool) -> str:
    """Значение в том виде, в каком оно напечатано на документе."""
    if key not in DATE_KEYS:
        return value
    year, month, day = (int(part) for part in value.split("-"))
    return f"{day} {MONTHS[month - 1]} {year} года" if worded else f"{day:02d}.{month:02d}.{year}"


def font_files() -> tuple[str | None, str | None]:
    for regular, bold in [
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        (
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
    ]:
        if Path(regular).exists() and Path(bold).exists():
            return regular, bold
    return None, None


def draw_signature(page: pymupdf.Page, x: float, y: float, rng: random.Random) -> None:
    ink = (0.098, 0.231, 0.439)
    points = []
    steps = rng.randint(26, 34)
    for index in range(steps):
        px = x + 10 + index * 80 / steps
        py = (
            y
            - 6
            + math.sin(index * rng.uniform(0.9, 1.6)) * rng.uniform(3, 9) * (1 - index / steps / 2)
        )
        points.append(pymupdf.Point(px, py))
    page.draw_polyline(points, color=ink, width=1.4)
    page.draw_line(pymupdf.Point(x + 7, y + 1), pymupdf.Point(x + 94, y - 11), color=ink, width=1.4)


def render(
    doc_id: str,
    doc_type: str,
    card: dict[str, str | bool],
    worded: bool,
    rng: random.Random,
    pdf_path: Path,
    png_path: Path,
    hand_font: str | None = None,
) -> None:
    spec = TYPES[doc_type]
    regular, bold = font_files()
    document = pymupdf.open()
    page = document.new_page(width=PAGE_W, height=PAGE_H)
    kwargs = {"fontname": "body", "fontfile": regular} if regular else {"fontname": "helv"}
    bold_kwargs = {"fontname": "head", "fontfile": bold} if bold else {"fontname": "hebo"}
    left = spec["left"]
    gray, dark = (0.45, 0.45, 0.45), (0.1, 0.13, 0.17)

    page.insert_text(
        (left, 33),
        "СИНТЕТИЧЕСКИЙ ДОКУМЕНТ ДЛЯ ХАКАТОНА / НЕ ИМЕЕТ ЮРИДИЧЕСКОЙ СИЛЫ",
        fontsize=8,
        color=gray,
        **kwargs,
    )
    page.insert_text((left, 78), spec["subtitle"], fontsize=10, color=dark, **kwargs)
    page.insert_text((left, 123), spec["title"], fontsize=16, color=dark, **bold_kwargs)
    page.insert_text((left, 164), spec["intro"], fontsize=11, color=dark, **kwargs)

    y = 201.0
    for key, label in spec["fields"]:
        value = card[key]
        text = "_" * 32 if value == "не найдено" else shown(key, str(value), worded)
        if hand_font and value != "не найдено":
            # Бланк с линией, значение вписано от руки синей ручкой.
            page.insert_text((left, y), f"{label}:", fontsize=11.5, color=dark, **kwargs)
            start = left + pymupdf.Font(fontfile=regular).text_length(f"{label}: ", fontsize=11.5)
            page.draw_line(
                pymupdf.Point(start, y + 2),
                pymupdf.Point(start + 215, y + 2),
                color=(0.6, 0.6, 0.6),
                width=0.5,
            )
            page.insert_text(
                (start + rng.uniform(2, 10), y + rng.uniform(-1.5, 1.0)),
                text,
                fontsize=rng.uniform(14.5, 16.5),
                color=(0.1, 0.2, 0.55),
                fontname="hand",
                fontfile=hand_font,
            )
        else:
            page.insert_text((left, y), f"{label}: {text}", fontsize=11.5, color=dark, **kwargs)
        y += 27.5

    page.insert_text((left, 653), f"{spec['signature']}:", fontsize=10, color=dark, **kwargs)
    line_x = left + 175
    page.draw_line(
        pymupdf.Point(line_x, 652),
        pymupdf.Point(line_x + 120, 652),
        color=(0.6, 0.6, 0.6),
        width=0.5,
    )
    if card["signature_present"]:
        draw_signature(page, line_x, 652, rng)
    if spec["seal"]:
        if card["seal_present"]:
            blue = (0.192, 0.341, 0.549)
            center = pymupdf.Point(473, 652)
            page.draw_circle(center, 41, color=blue, width=1.5)
            page.draw_circle(center, 35, color=blue, width=1.5)
            for offset, word, size, face in [
                (-11, "УЧЕБНАЯ", 8, bold_kwargs),
                (0, "ПЕЧАТЬ", 8, bold_kwargs),
                (12, "МАКЕТ", 7, kwargs),
            ]:
                source = bold if face is bold_kwargs else regular
                measure = pymupdf.Font(fontfile=source) if source else pymupdf.Font("helv")
                width = measure.text_length(word, fontsize=size)
                page.insert_text(
                    (473 - width / 2, 652 + offset),
                    word,
                    fontsize=size,
                    color=blue,
                    **face,
                )
        page.insert_text((445, 708), "М.П.", fontsize=9, color=dark, **kwargs)

    page.insert_text(
        (left, 787),
        "Все сведения вымышлены. Подпись и печать являются учебными макетами.",
        fontsize=7,
        color=gray,
        **kwargs,
    )
    page.insert_text(
        (left, 802),
        f"Идентификатор образца: {doc_id}",
        fontsize=7,
        color=gray,
        **kwargs,
    )

    document.save(pdf_path, deflate=True)
    zoom = PNG_WIDTH / PAGE_W
    page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False).save(png_path)
    document.close()


def reference(
    doc_id: str, doc_type: str, card: dict[str, str | bool], rng: random.Random
) -> tuple[dict, list[dict]]:
    spec = TYPES[doc_type]
    rules = spec["rules"]
    missing = [key for key, value in card.items() if value == "не найдено" or value is False]
    if missing:
        used = sorted({rules.get(key, rules["text"]) for key in missing})
        status = "missing_fields"
    else:
        used = sorted(set(rules.values()))
        status = "document_ok"
    sources = [f"rule:{rule}" for rule in used]
    validation = {"status": status, "missing_fields": missing, "sources": sources}

    text_fields = spec["fields"]
    key, label = rng.choice(text_fields)
    questions = [
        (
            "Содержит ли документ все обязательные сведения по Положению?",
            {"answerable": True, "value": status, "sources": sources},
        ),
        (
            f"Укажи значение поля «{label}».",
            {"answerable": False, "value": None, "sources": []}
            if card[key] == "не найдено"
            else {"answerable": True, "value": card[key], "sources": [f"field:{key}"]},
        ),
        (
            "Кто принимает окончательное решение о принятии документа?",
            {
                "answerable": True,
                "value": "сотрудник деканата",
                "sources": ["rule:1.3"],
            },
        ),
        (rng.choice(UNANSWERABLE), {"answerable": False, "value": None, "sources": []}),
    ]
    asked, answers = [], []
    for index, (question, expected) in enumerate(questions, start=1):
        question_id = f"{doc_id}-Q{index}"
        asked.append({"question_id": question_id, "document_id": doc_id, "question": question})
        answers.append({"question_id": question_id, **expected, "answer": "эталон"})
    record = {
        "document_id": doc_id,
        "document_type": doc_type,
        "fields": card,
        "validation": validation,
        "answers": answers,
    }
    return record, asked


HAND_FONTS = [
    "C:/Windows/Fonts/MISTRAL.TTF",
    "C:/Windows/Fonts/Gabriola.ttf",
    "C:/Windows/Fonts/comic.ttf",
]


def build(
    out: Path, count: int, seed: int, prefix: str = "synth", handwritten: bool = False
) -> None:
    fonts = [font for font in HAND_FONTS if Path(font).exists()] if handwritten else []
    if handwritten and not fonts:
        raise SystemExit("Не найдены рукописные шрифты: режим --handwritten работает в Windows.")
    rng = random.Random(seed)
    (out / "documents").mkdir(parents=True, exist_ok=True)
    manifest, questions, records = [], [], []
    type_ids = list(TYPES)
    for index in range(1, count + 1):
        doc_type = type_ids[(index - 1) % len(type_ids)]
        doc_id = f"{prefix}-{index:03d}"
        card: dict[str, str | bool] = dict(values(doc_type, rng, rng.randint(1000, 9999)))
        # Треть документов полные, остальные с одним-тремя пропусками.
        gaps = rng.choice([0, 0, 1, 1, 1, 2, 2, 3])
        for key in rng.sample(list(card), k=min(gaps, len(card))):
            card[key] = "не найдено"
        card["signature_present"] = rng.random() > 0.25
        if TYPES[doc_type]["seal"]:
            card["seal_present"] = rng.random() > 0.25
        pdf_path = out / "documents" / f"{doc_id}.pdf"
        png_path = out / "documents" / f"{doc_id}.png"
        hand = fonts[index % len(fonts)] if fonts else None
        render(doc_id, doc_type, card, rng.random() < 0.5, rng, pdf_path, png_path, hand)
        record, asked = reference(doc_id, doc_type, card, rng)
        records.append(record)
        questions.extend(asked)
        manifest.append(
            {
                "document_id": doc_id,
                "document_type": doc_type,
                "image": f"documents/{doc_id}.png",
                "pdf": f"documents/{doc_id}.pdf",
            }
        )

    def dump(name: str, data: object) -> None:
        (out / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    dump("documents.json", manifest)
    dump("questions.json", questions)
    dump("reference_results.json", {"version": "1.0", "documents": records})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("data/synth"))
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--handwritten", action="store_true", help="значения вписаны от руки")
    arguments = parser.parse_args()
    build(
        arguments.out,
        arguments.count,
        arguments.seed,
        handwritten=arguments.handwritten,
    )
    print(f"Готово: {arguments.count} документов в {arguments.out}")
