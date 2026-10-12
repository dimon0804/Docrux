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
