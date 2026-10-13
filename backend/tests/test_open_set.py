"""Сверка с эталоном организаторов на открытом наборе."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from paragraf.batch import run_batch
from paragraf.pipeline import Pipeline


def _evaluator(open_dir: Path):
    spec = importlib.util.spec_from_file_location("evaluate", open_dir / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def results(pipeline: Pipeline, open_dir: Path) -> dict:
    return run_batch(
        pipeline, open_dir / "documents.json", open_dir / "questions.json", source="pdf"
    )


def test_matches_reference_on_every_metric(results: dict, open_dir: Path):
    reference = json.loads((open_dir / "reference_results.json").read_text(encoding="utf-8"))
    report = _evaluator(open_dir).evaluate(reference, results)
    assert report["errors"] == []
    assert report["field_accuracy_macro"] == 1.0
    assert report["validation_exact_match"] == 1.0
    assert report["question_exact_match"] == 1.0


def _schema_errors(open_dir: Path, data: dict) -> list[str]:
    import jsonschema

    schema = json.loads((open_dir / "results.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [f"{list(error.path)}: {error.message}" for error in validator.iter_errors(data)]


def test_results_follow_the_organizers_schema(results: dict, open_dir: Path):
    assert _schema_errors(open_dir, results) == []


def test_answer_text_agrees_with_structured_value(results: dict):
    """Текст ответа не должен противоречить value: это проверяют на защите."""
    for document in results["documents"]:
        status = document["validation"]["status"]
        for answer in document["answers"]:
            text = answer["answer"]
            if answer["value"] == "document_ok":
                assert "все обязательные сведения" in text
                assert status == "document_ok"
            elif answer["value"] == "missing_fields":
                assert text.startswith("Не хватает")
            elif answer["answerable"] and answer["sources"][0].startswith("field:"):
                assert answer["value"] in text
            if not answer["answerable"]:
                assert answer["value"] is None and answer["sources"] == []


def test_missing_fields_are_named_in_the_answer(results: dict, pipeline: Pipeline):
    for document in results["documents"]:
        doc_type = pipeline.registry.get(document["document_type"])
        for answer in document["answers"]:
            if answer["value"] != "missing_fields":
                continue
            for key in document["validation"]["missing_fields"]:
                label = doc_type.field(key).label
                assert label.casefold() in answer["answer"].casefold()


def test_one_broken_file_does_not_stop_the_batch(
    pipeline: Pipeline, open_dir: Path, tmp_path: Path
):
    """Битый файл в наборе даёт пустую карточку, а не падение всего прогона."""
    (tmp_path / "documents").mkdir()
    good = (open_dir / "documents" / "open-001.pdf").read_bytes()
    (tmp_path / "documents" / "good.pdf").write_bytes(good)
    (tmp_path / "documents" / "broken.pdf").write_bytes(b"%PDF-1.7 this is not a real pdf")
    manifest = [
        {"document_id": "a", "document_type": "study_certificate", "pdf": "documents/good.pdf"},
        {
            "document_id": "b",
            "document_type": "internship_certificate",
            "pdf": "documents/broken.pdf",
        },
        {"document_id": "c", "document_type": "study_certificate", "pdf": "documents/missing.pdf"},
    ]
    questions = [
        {
            "question_id": "b-Q1",
            "document_id": "b",
            "question": "Содержит ли документ все обязательные сведения по Положению?",
        },
        {"question_id": "b-Q2", "document_id": "b", "question": "Укажи значение поля «Оценка»."},
    ]
    (tmp_path / "documents.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "questions.json").write_text(
        json.dumps(questions, ensure_ascii=False), encoding="utf-8"
    )
    notes: list[str] = []
    result = run_batch(
        pipeline,
        tmp_path / "documents.json",
        tmp_path / "questions.json",
        source="pdf",
        progress=notes.append,
    )
    by_id = {doc["document_id"]: doc for doc in result["documents"]}
    assert by_id["a"]["validation"]["status"] == "document_ok"
    broken = by_id["b"]
    assert broken["document_type"] == "internship_certificate"
    assert set(broken["fields"]) == set(pipeline.registry.get("internship_certificate").keys)
    assert broken["fields"]["grade"] == "не найдено" and broken["fields"]["seal_present"] is False
    assert broken["validation"]["status"] == "missing_fields"
    assert broken["answers"][0]["value"] == "missing_fields"
    assert broken["answers"][1] == {
        **broken["answers"][1],
        "answerable": False,
        "value": None,
        "sources": [],
    }
    assert by_id["c"]["validation"]["status"] == "missing_fields"
    assert any("ВНИМАНИЕ" in note for note in notes)
    assert _schema_errors(open_dir, result) == []
