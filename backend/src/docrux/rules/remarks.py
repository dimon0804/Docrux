"""Замечания для сотрудника: сведения на месте, но выглядят странно.

Положение требует только наличия сведений (пункты 2.2 и 2.6), поэтому замечания
на итог проверки не влияют. Это подсказка сотруднику, куда посмотреть
внимательнее: окончание раньше начала, справка из будущего, курс «9».

Проверки опираются на типы и названия полей, а не на конкретный документ:
пара «*_start» и «*_end» сверяется у любого типа, в том числе нового.
"""

from __future__ import annotations

import re
from datetime import date

from docrux.doctypes import DocType
from docrux.models import FieldValue, Remark

# Даты, которые описывают сам документ, а не период: они не могут быть в будущем.
_DOCUMENT_DATES = ("issue_date", "application_date")
_LONG_PERIOD_DAYS = {"leave": 2 * 366, "internship": 366, "study": 7 * 366}
_PROGRAM_CODE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{2})\b")
# Вторая пара цифр шифра по классификатору ОКСО — уровень образования.
LEVELS = {
    "01": "СПО, профессия",
    "02": "СПО, специальность",
    "03": "бакалавриат",
    "04": "магистратура",
    "05": "специалитет",
    "06": "аспирантура",
    "07": "адъюнктура",
    "08": "ординатура",
    "09": "ассистентура-стажировка",
}
MAX_GROUP = 58
"""Укрупнённые группы направлений в ОКСО занимают номера от 01 до 58."""
_KNOWN_GRADES = {
    "отлично",
    "хорошо",
    "удовлетворительно",
    "неудовлетворительно",
    "зачтено",
    "не зачтено",
    "зачёт",
    "зачет",
}


def _date(field: FieldValue | None) -> date | None:
    if field is None or not field.found or not isinstance(field.value, str):
        return None
    try:
        return date.fromisoformat(field.value)
    except ValueError:
        return None


def _human(day: date) -> str:
    return day.strftime("%d.%m.%Y")


def find_remarks(
    doc_type: DocType, fields: list[FieldValue], today: date | None = None
) -> list[Remark]:
    today = today or date.today()
    by_key = {field.key: field for field in fields}
    label = {field.key: field.label for field in fields}
    out: list[Remark] = []

    def add(text: str, *keys: str) -> None:
        out.append(Remark(text=text, fields=[key for key in keys if key in by_key]))

    # Периоды: начало и окончание.
    for key in by_key:
        if not key.endswith("_start"):
            continue
        prefix = key[: -len("_start")]
        end_key = prefix + "_end"
        start, end = _date(by_key[key]), _date(by_key.get(end_key))
        if start is None or end is None:
            continue
        if end < start:
            add(
                f"«{label[end_key]}» ({_human(end)}) раньше, чем «{label[key]}» ({_human(start)}).",
                key,
                end_key,
            )
        elif (end - start).days > _LONG_PERIOD_DAYS.get(prefix, 10 * 366):
            years = (end - start).days / 365.25
            add(
                f"Период от «{label[key]}» до «{label[end_key]}» длится около "
                f"{years:.0f} {'года' if 1 < round(years) < 5 else 'лет'}. Проверьте даты.",
                key,
                end_key,
            )

    # Дата документа не может быть позже сегодняшнего дня.
    for key in _DOCUMENT_DATES:
        day = _date(by_key.get(key))
        if day is not None and day > today:
            add(f"«{label[key]}» ({_human(day)}) позже сегодняшнего дня.", key)

    issued = _date(by_key.get("issue_date"))
    study_start = _date(by_key.get("study_start"))
    if issued and study_start and issued < study_start:
        add("Справка выдана раньше, чем началось обучение.", "issue_date", "study_start")
    practice_end = _date(by_key.get("internship_end"))
    if issued and practice_end and issued < practice_end:
        add("Справка о практике выдана до окончания практики.", "issue_date", "internship_end")
    applied = _date(by_key.get("application_date"))
    leave_start = _date(by_key.get("leave_start"))
    if applied and leave_start and applied > leave_start:
        add("Заявление подано после даты начала отпуска.", "application_date", "leave_start")

    course = by_key.get("course")
    if (
        course
        and course.found
        and str(course.value).isdigit()
        and not 1 <= int(str(course.value)) <= 6
    ):
        add(f"Курс «{course.value}» вне обычного диапазона от 1 до 6.", "course")

    program = by_key.get("program")
    if program and program.found and isinstance(program.value, str):
        value = program.value.strip()
        code = _PROGRAM_CODE.match(value)
        if re.match(r"^\d", value) and not code:
            add("Шифр направления не похож на формат 00.00.00.", "program")
        elif code and code.group(2) not in LEVELS:
            add(
                f"В шифре {code.group(0)} вторая пара цифр «{code.group(2)}» не обозначает "
                "уровень образования по классификатору ОКСО.",
                "program",
            )
        elif code and not 1 <= int(code.group(1)) <= MAX_GROUP:
            add(
                f"В шифре {code.group(0)} нет такой укрупнённой группы направлений: "
                f"«{code.group(1)}».",
                "program",
            )

    grade = by_key.get("grade")
    if (
        grade
        and grade.found
        and isinstance(grade.value, str)
        and grade.value.strip().lower() not in _KNOWN_GRADES
    ):
        add(f"Оценка «{grade.value}» не из обычного списка: проверьте по снимку.", "grade")

    student, supervisor = by_key.get("student_name"), by_key.get("supervisor_name")
    if (
        student
        and supervisor
        and student.found
        and supervisor.found
        and str(student.value).strip().lower() == str(supervisor.value).strip().lower()
    ):
        add("ФИО студента и руководителя практики совпадают.", "student_name", "supervisor_name")
    return out
