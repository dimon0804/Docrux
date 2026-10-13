"""Генератор документов свободной формы: сплошной текст вместо строк «Метка: значение».

Так выглядят настоящие справки и заявления. Набор нужен, чтобы измерить,
находит ли сервис сведения в связном тексте и определяет ли тип документа сам.

    python tools/freeform.py --out data/synth-free --count 45
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

import pymupdf
from synth import (
    GRADES,
    GROUP_PREFIXES,
    MONTHS,
    ORGANIZATIONS,
    PROGRAMS,
    STUDY_FORMS,
    UNIVERSITIES,
    draw_signature,
    font_files,
    person,
)

DATIVE = {"очная": "очной", "заочная": "заочной", "очно-заочная": "очно-заочной"}


def to_case(fio: str, case: str) -> str:
    import pymorphy3

    morph = to_case.morph = getattr(to_case, "morph", None) or pymorphy3.MorphAnalyzer()
    gender = "femn" if fio.split()[2].endswith("на") else "masc"
    out = []
    for word, kind in zip(fio.split(), ("Surn", "Name", "Patr"), strict=True):
        pieces = []
        for piece in word.split("-"):
            parses = sorted(
                morph.parse(piece),
                key=lambda p: (kind in p.tag, p.tag.gender == gender, "nomn" in p.tag),
                reverse=True,
            )
            form = parses[0].inflect({case}) if parses else None
            result = form.word if form else piece
            pieces.append(result[:1].upper() + result[1:])
        out.append("-".join(pieces))
    return " ".join(out)


def fmt(iso: str, worded: bool) -> str:
    year, month, day = (int(part) for part in iso.split("-"))
    return (
        f"{day} {MONTHS[month - 1]} {year} года"
        if worded
        else f"{day:02d}.{month:02d}.{year}"
    )


def day(rng: random.Random, start: date, spread: int) -> str:
    return (start + timedelta(days=rng.randrange(spread))).isoformat()


def study(rng: random.Random, variant: int):
    fio = person(rng, female=rng.random() < 0.4)
    card = {
        "student_name": fio,
        "university": rng.choice(UNIVERSITIES),
        "program": rng.choice(PROGRAMS),
        "study_form": rng.choice(STUDY_FORMS),
        "study_start": f"{rng.choice([2022, 2023, 2024])}-09-01",
        "study_end": day(rng, date(2027, 6, 1), 60),
        "document_number": f"{rng.randint(10, 999)}/{rng.randint(1, 9)}",
        "issue_date": day(rng, date(2026, 9, 1), 40),
    }
    w = rng.random() < 0.5
    female = fio.split()[2].endswith("на")
    he, student = ("она", "студенткой") if female else ("он", "студентом")
    if variant == 0:
        title = "СПРАВКА"
        head = f"{card['university']}\n№ {card['document_number']} от {fmt(card['issue_date'], w)}"
        body = (
            f"Дана {to_case(fio, 'datv')} в том, что {he} действительно является {student} "
            f"{rng.randint(1, 4)} курса {DATIVE[card['study_form']]} формы обучения по направлению подготовки "
            f"{card['program']}. Срок обучения с {fmt(card['study_start'], w)} по "
            f"{fmt(card['study_end'], w)}.\n\nСправка выдана для предъявления по месту требования."
        )
    elif variant == 1:
        title = "СПРАВКА ОБ ОБУЧЕНИИ"
        head = f"Справка № {card['document_number']} от {fmt(card['issue_date'], w)}"
        body = (
            f"Настоящая справка выдана {to_case(fio, 'datv')} и подтверждает, что {he} обучается в "
            f"{card['university']}, {card['program']}, {card['study_form']} форма обучения. "
            f"Период обучения с {fmt(card['study_start'], w)} по {fmt(card['study_end'], w)}."
        )
    else:
        title = "СПРАВКА"
        head = f"{card['university']}\nИсх. № {card['document_number']} от {fmt(card['issue_date'], w)}"
        body = (
            f"Выдана {to_case(fio, 'datv')}. Зачислен{'а' if female else ''} приказом ректора "
            f"и обучается с {fmt(card['study_start'], w)} по {fmt(card['study_end'], w)} на "
            f"{DATIVE[card['study_form']]} форме обучения. Направление подготовки: {card['program']}."
        )
    return card, title, head, body, "Декан факультета", True


def internship(rng: random.Random, variant: int):
    fio = person(rng, female=rng.random() < 0.4)
    boss = person(rng, female=rng.random() < 0.5)
    card = {
        "student_name": fio,
        "organization": rng.choice(ORGANIZATIONS),
        "internship_start": day(rng, date(2026, 5, 20), 20),
        "internship_end": day(rng, date(2026, 7, 1), 25),
        "supervisor_name": boss,
        "grade": rng.choice(GRADES),
        "document_number": f"{rng.randint(10, 999)}",
        "issue_date": day(rng, date(2026, 7, 26), 20),
    }
    w = rng.random() < 0.5
    female = fio.split()[2].endswith("на")
    passed = "проходила" if female else "проходил"
    title = "СПРАВКА О ПРОХОЖДЕНИИ ПРАКТИКИ" if variant == 0 else "СПРАВКА"
    head = f"№ {card['document_number']} от {fmt(card['issue_date'], w)}"
    if variant == 0:
        body = (
            f"Дана {to_case(fio, 'datv')} в том, что {'она' if female else 'он'} {passed} "
            f"производственную практику в {card['organization']} с {fmt(card['internship_start'], w)} "
            f"по {fmt(card['internship_end'], w)}. Руководитель практики от организации: {boss}. "
            f"По итогам практики выставлена оценка «{card['grade']}»."
        )
    else:
        body = (
            f"Студент {to_case(fio, 'nomn')} {passed} практику в период с "
            f"{fmt(card['internship_start'], w)} по {fmt(card['internship_end'], w)} на базе "
            f"{card['organization']}. Руководитель практики {boss}. Оценка: {card['grade']}."
        )
    return card, title, head, body, "Руководитель практики", True


def leave(rng: random.Random, variant: int):
    fio = person(rng, female=rng.random() < 0.4)
    reasons = [
        "по состоянию здоровья",
        "по семейным обстоятельствам",
        "в связи с призывом на военную службу",
        "в связи с уходом за родственником",
    ]
    card = {
        "student_name": fio,
        "group": f"{rng.choice(GROUP_PREFIXES)}-{rng.randint(20, 26)}-{rng.randint(1, 9)}",
        "course": str(rng.randint(1, 4)),
        "leave_reason": rng.choice(reasons),
        "leave_start": day(rng, date(2026, 10, 20), 40),
        "leave_end": day(rng, date(2027, 7, 1), 60),
        "application_date": day(rng, date(2026, 9, 25), 20),
    }
    w = rng.random() < 0.5
    title = "ЗАЯВЛЕНИЕ"
    head = (
        f"Декану факультета\nот студента {card['course']} курса группы {card['group']}\n"
        f"{to_case(fio, 'gent')}"
    )
    if variant == 0:
        body = (
            f"Прошу предоставить мне академический отпуск {card['leave_reason']} с "
            f"{fmt(card['leave_start'], w)} по {fmt(card['leave_end'], w)}.\n\n"
            f"Дата: {fmt(card['application_date'], w)}"
        )
    else:
        body = (
            f"Прошу предоставить академический отпуск с {fmt(card['leave_start'], w)} по "
            f"{fmt(card['leave_end'], w)} {card['leave_reason']}.\n\n"
            f"Дата: {fmt(card['application_date'], w)}"
        )
    return card, title, head, body, "Подпись", False


MAKERS = [
    ("study_certificate", study, 3),
    ("academic_leave_application", leave, 2),
    ("internship_certificate", internship, 2),
]


def render(
    path_pdf: Path,
    path_png: Path,
    title: str,
    head: str,
    body: str,
    signer: str,
    seal: bool,
    signed: bool,
    sealed: bool,
    rng: random.Random,
) -> None:
    regular, bold = font_files()
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    plain = {"fontname": "body", "fontfile": regular}
    strong = {"fontname": "head", "fontfile": bold}
    dark = (0.1, 0.1, 0.12)
    page.insert_textbox(
        pymupdf.Rect(300, 50, 545, 130),
        head,
        fontsize=11,
        color=dark,
        align=pymupdf.TEXT_ALIGN_LEFT,
        **plain,
    )
    width = pymupdf.Font(fontfile=bold).text_length(title, fontsize=15)
    page.insert_text(((595 - width) / 2, 180), title, fontsize=15, color=dark, **strong)
    page.insert_textbox(
        pymupdf.Rect(60, 210, 540, 520),
        body,
        fontsize=12,
        color=dark,
        lineheight=1.6,
        align=pymupdf.TEXT_ALIGN_JUSTIFY,
        **plain,
    )
    y = 600
    page.insert_text((60, y), f"{signer}:", fontsize=11, color=dark, **plain)
    page.draw_line(
        pymupdf.Point(230, y), pymupdf.Point(350, y), color=(0.6, 0.6, 0.6), width=0.5
    )
    if signed:
        draw_signature(page, 230, y, rng)
    if seal:
        if sealed:
            blue = (0.19, 0.34, 0.55)
            page.draw_circle(pymupdf.Point(470, y), 40, color=blue, width=1.5)
            page.draw_circle(pymupdf.Point(470, y), 34, color=blue, width=1.2)
        page.insert_text((445, y + 58), "М.П.", fontsize=9, color=dark, **plain)
    document.save(path_pdf, deflate=True)
    page.get_pixmap(matrix=pymupdf.Matrix(1132 / 595, 1132 / 595), alpha=False).save(
        path_png
    )
    document.close()


def build(out: Path, count: int, seed: int) -> None:
    rng = random.Random(seed)
    (out / "documents").mkdir(parents=True, exist_ok=True)
    manifest, records = [], []
    for index in range(1, count + 1):
        type_id, maker, variants = MAKERS[(index - 1) % len(MAKERS)]
        card, title, head, body, signer, has_seal = maker(
            rng, (index // len(MAKERS)) % variants
        )
        signed, sealed = rng.random() > 0.2, rng.random() > 0.2
        fields: dict[str, str | bool] = dict(card)
        fields["signature_present"] = signed
        if has_seal:
            fields["seal_present"] = sealed
        doc_id = f"free-{index:03d}"
        render(
            out / "documents" / f"{doc_id}.pdf",
            out / "documents" / f"{doc_id}.png",
            title,
            head,
            body,
            signer,
            has_seal,
            signed,
            sealed,
            rng,
        )
        manifest.append(
            {
                "document_id": doc_id,
                "document_type": type_id,
                "image": f"documents/{doc_id}.png",
                "pdf": f"documents/{doc_id}.pdf",
            }
        )
        records.append(
            {"document_id": doc_id, "document_type": type_id, "fields": fields}
        )
    (out / "documents.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "reference_fields.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("data/synth-free"))
    parser.add_argument("--count", type=int, default=45)
    parser.add_argument("--seed", type=int, default=5)
    arguments = parser.parse_args()
    build(arguments.out, arguments.count, arguments.seed)
    print(f"Готово: {arguments.count} документов в {arguments.out}")
