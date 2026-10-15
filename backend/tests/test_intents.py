import pytest

from docrux.doctypes import DocTypeRegistry
from docrux.qa.intents import detect

STUDY = "study_certificate"
LEAVE = "academic_leave_application"
PRACTICE = "internship_certificate"


@pytest.mark.parametrize(
    "question",
    [
        "Содержит ли документ все обязательные сведения по Положению?",
        "Содержит ли документ все обязательные сведения?",
        "Прикладываю фото справки из прошлого вуза. Хватит ли её для перевода на 2 курс?",
        "Подходит ли документ?",
        "Чего не хватает в справке?",
        "Всё ли в порядке с документом?",
        "Проверь документ",
        "Правильно ли заполнено заявление?",
        "Каких полей не хватает?",
        "Что нужно исправить?",
        "Достаточно ли этой справки?",
        "Примут ли мою справку?",
        "Документ соответствует требованиям Положения?",
    ],
)
def test_completeness(registry: DocTypeRegistry, question):
    assert detect(registry.get(STUDY), question).kind == "completeness"


@pytest.mark.parametrize(
    "question",
    [
        "Кто принимает окончательное решение о принятии документа?",
        "Кто решает, примут документ или нет?",
        "Кем принимается окончательное решение?",
        "За кем окончательное решение?",
        "Кто утверждает заявление?",
    ],
)
def test_decision(registry: DocTypeRegistry, question):
    assert detect(registry.get(LEAVE), question).kind == "decision"


@pytest.mark.parametrize(
    ("type_id", "question", "key"),
    [
        (STUDY, "Укажи значение поля «ФИО студента».", "student_name"),
        (STUDY, "Укажи значение поля «Дата выдачи».", "issue_date"),
        (STUDY, "Укажи значение поля «Окончание периода обучения».", "study_end"),
        (STUDY, 'Укажи значение поля "Название вуза".', "university"),
        (STUDY, "Какова дата выдачи?", "issue_date"),
        (STUDY, "Когда выдана справка?", "issue_date"),
        (STUDY, "Как зовут студента?", "student_name"),
        (STUDY, "Какая форма обучения?", "study_form"),
        (STUDY, "Какой номер у справки?", "document_number"),
        (STUDY, "На каком направлении учится студент?", "program"),
        (STUDY, "Когда началось обучение?", "study_start"),
        (STUDY, "Есть ли печать на справке?", "seal_present"),
        (STUDY, "Есть ли подпись?", "signature_present"),
        (LEAVE, "Укажи значение поля «Учебная группа».", "group"),
        (LEAVE, "Укажи значение поля «Курс».", "course"),
        (LEAVE, "На каком курсе учится студент?", "course"),
        (LEAVE, "В какой группе учится студент?", "group"),
        (LEAVE, "Какая причина отпуска?", "leave_reason"),
        (LEAVE, "Когда начинается отпуск?", "leave_start"),
        (LEAVE, "Дата окончания отпуска?", "leave_end"),
        (LEAVE, "Когда написано заявление?", "application_date"),
        (PRACTICE, "Укажи значение поля «ФИО руководителя практики».", "supervisor_name"),
        (PRACTICE, "Кто руководитель практики?", "supervisor_name"),
        (PRACTICE, "Какую оценку получил студент?", "grade"),
        (PRACTICE, "Где студент проходил практику?", "organization"),
        (PRACTICE, "Дата окончания практики", "internship_end"),
        (PRACTICE, "Когда началась практика?", "internship_start"),
        (PRACTICE, "Какой номер справки?", "document_number"),
    ],
)
def test_field(registry: DocTypeRegistry, type_id, question, key):
    intent = detect(registry.get(type_id), question)
    assert intent.kind == "field"
    assert intent.field is not None and intent.field.key == key


@pytest.mark.parametrize(
    "question",
    [
        "Какова стоимость обучения за следующий семестр?",
        "Какой размер стипендии положен студенту?",
        "Какой срок рассмотрения документа деканатом?",
        "По какому номеру телефона можно связаться с деканатом?",
        "В каком кабинете принимают оригиналы документов?",
        "Сколько стоит общежитие?",
        "Какая погода завтра?",
        "Когда каникулы?",
        "Как зовут декана?",
        "Какой адрес у вуза?",
        "Какой номер аудитории?",
        "Когда выплатят стипендию студенту?",
        "Сколько длится академический отпуск по правилам?",
        "Расскажи анекдот",
        "",
    ],
)
@pytest.mark.parametrize("type_id", [STUDY, LEAVE, PRACTICE])
def test_unknown(registry: DocTypeRegistry, type_id, question):
    assert detect(registry.get(type_id), question).kind == "unknown"


def test_quoted_label_from_another_type_is_unknown(registry: DocTypeRegistry):
    intent = detect(registry.get(STUDY), "Укажи значение поля «Учебная группа».")
    assert intent.kind == "unknown"
