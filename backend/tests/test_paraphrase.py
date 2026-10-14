"""Вопросы открытого набора, заданные другими словами.

Закрытый набор может формулировать вопросы иначе, чем открытый. Каждый вопрос
переписывается несколькими способами; ответ в строгом режиме (тот, что идёт в
results.json) должен совпасть с эталоном исходного вопроса.
"""

from __future__ import annotations

import json
import re

import pytest

from paragraf.pipeline import Pipeline

COMPLETE = [
    "Содержит ли документ все обязательные сведения по Положению?",
    "Все ли обязательные сведения есть в документе?",
    "Хватает ли в документе обязательных сведений?",
    "Документ полный?",
    "Чего не хватает в документе?",
    "Все ли данные на месте?",
    "Проверь документ на комплектность.",
    "Соответствует ли документ требованиям Положения?",
    "Есть ли в документе все необходимые данные?",
    "Подходит ли документ?",
    "Полный ли документ?",
    "Всё ли заполнено?",
    "Все ли сведения указаны?",
    "Документ в порядке?",
    "Справка заполнена полностью?",
    "Каких сведений нет в документе?",
]
DECISION = [
    "Кто принимает окончательное решение о принятии документа?",
    "Кто принимает окончательное решение?",
    "Кто примет решение по документу?",
    "Кто решает, примут ли документ?",
    "Кто окончательно решает по заявлению?",
    "Кто принимает решение о принятии справки?",
    "За кем окончательное решение?",
]
FIELD = [
    "Укажи значение поля «{label}».",
    "Какое значение у поля «{label}»?",
    "Что указано в поле «{label}»?",
    "Что написано в поле «{label}»?",
    "Назови значение поля «{label}».",
    "Какое значение поля «{label}»?",
    "{label}?",
    "Какой {label_lower} указан в документе?",
    "Укажи {label_lower}.",
    "Значение поля {label}",
]
UNKNOWN_EXTRA = [
    "Сколько стоит обучение?",
    "Когда начинаются каникулы?",
    "Где находится общежитие?",
    "Какая зарплата у декана?",
    "Можно ли перевестись на бюджет?",
]


def _variants(text: str) -> list[str]:
    match = re.search(r"«([^»]+)»", text)
    if text.startswith("Содержит ли"):
        return COMPLETE
    if text.startswith("Кто принимает"):
        return DECISION
    if match:
        label = match.group(1)
        lower = label if label[:2].isupper() else label[0].lower() + label[1:]
        return [variant.format(label=label, label_lower=lower) for variant in FIELD]
    return [text, *UNKNOWN_EXTRA]


@pytest.fixture(scope="module")
def cases(pipeline: Pipeline, open_dir):
    questions = json.loads((open_dir / "questions.json").read_text(encoding="utf-8"))
    reference = json.loads((open_dir / "reference_results.json").read_text(encoding="utf-8"))
    answers = {
        (doc["document_id"], answer["question_id"]): answer
        for doc in reference["documents"]
        for answer in doc["answers"]
    }
    analyses = {}
    out = []
    for item in questions:
        doc_id = item["document_id"]
        if doc_id not in analyses:
            data = (open_dir / "documents" / f"{doc_id}.pdf").read_bytes()
            analyses[doc_id] = pipeline.analyze(data).analysis
        expected = answers[(doc_id, item["question_id"])]
        for variant in _variants(item["question"]):
            out.append((analyses[doc_id], variant, expected))
    return out


def test_paraphrased_questions_get_the_reference_answer(pipeline: Pipeline, cases):
    wrong = []
    for analysis, question, expected in cases:
        answer = pipeline.ask(analysis, question)
        got = (answer.answerable, answer.value, sorted(answer.sources))
        want = (expected["answerable"], expected["value"], sorted(expected["sources"]))
        if got != want:
            wrong.append((analysis.document_type, question, want, got))
    assert len(cases) > 1000
    assert wrong == []


TRICKY = [
    "Какой срок рассмотрения заявления на академический отпуск?",
    "Сколько дней рассматривают справку об обучении?",
    "Можно ли продлить академический отпуск?",
    "Сохранится ли стипендия во время отпуска?",
    "Какие причины отпуска допустимы?",
    "Сколько раз можно брать академический отпуск?",
    "Где получить справку о практике?",
    "Сколько стоит справка об обучении?",
    "Какую оценку нужно получить за практику, чтобы её зачли?",
    "Как перевестись на другую форму обучения?",
    "Можно ли перевестись на бюджет с этой справкой?",
    "Как связаться с руководителем практики?",
    "Какой телефон у вуза?",
    "Какой адрес у организации, где проходила практика?",
    "Нужно ли заверять справку у нотариуса?",
    "Сколько длится рассмотрение документов?",
    "Когда выдадут диплом?",
    "Какая стипендия у студента?",
    "Какой номер приказа о зачислении?",
    "Как зовут декана факультета?",
    "В какой срок нужно подать заявление?",
    "Можно ли отправить документ по почте?",
    "Какой график работы деканата?",
    "Сколько студентов в группе?",
    "Какой средний балл у студента?",
]


@pytest.mark.parametrize("doc_id", ["open-001", "open-012", "open-021"])
def test_off_topic_questions_with_document_words_are_refused(pipeline: Pipeline, open_dir, doc_id):
    analysis = pipeline.analyze((open_dir / "documents" / f"{doc_id}.pdf").read_bytes()).analysis
    answered = [q for q in TRICKY if pipeline.ask(analysis, q).answerable]
    assert answered == []
