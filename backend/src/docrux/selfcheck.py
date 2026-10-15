"""Самопроверка на открытом наборе организаторов прямо из интерфейса.

Сервис по очереди читает 30 документов, отвечает на 120 вопросов и после
каждого документа сообщает, что совпало с эталоном. В конце метрики считает
скрипт организаторов evaluate.py, тот же, что в CI, поэтому цифры на странице
и в отчёте автопроверки не расходятся.
"""

from __future__ import annotations

import importlib.util
import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from docrux.batch import (
    RESULTS_VERSION,
    _analyze,
    document_record,
    load_manifest,
    load_questions,
)
from docrux.pipeline import Pipeline


def _evaluator(open_dir: Path):
    spec = importlib.util.spec_from_file_location("organizers_evaluate", open_dir / "evaluate.py")
    if spec is None or spec.loader is None:
        raise FileNotFoundError("в наборе нет evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def available(open_dir: Path | None) -> bool:
    return bool(
        open_dir
        and (open_dir / "documents.json").is_file()
        and (open_dir / "reference_results.json").is_file()
        and (open_dir / "evaluate.py").is_file()
    )


def run(pipeline: Pipeline, open_dir: Path) -> Iterator[dict[str, Any]]:
    """События самопроверки: по одному на документ и итоговое с метриками."""
    evaluate = _evaluator(open_dir)
    reference = json.loads((open_dir / "reference_results.json").read_text(encoding="utf-8"))
    expected = {doc["document_id"]: doc for doc in reference["documents"]}
    asked = load_questions(open_dir / "questions.json")
    manifest = load_manifest(open_dir / "documents.json")
    documents: list[dict[str, Any]] = []
    yield {"type": "start", "documents": len(manifest)}
    for entry in manifest:
        started = time.perf_counter()
        document_id = entry["document_id"]
        # Ровно так же, как пакетный прогон для results.json: снимок, тип из манифеста.
        analysis = _analyze(pipeline, open_dir, entry, "image", [])
        record = document_record(pipeline, document_id, analysis, asked.get(document_id, []))
        documents.append(record)
        ref = expected.get(document_id)
        fields_ok = sum(
            1
            for key, value in (ref["fields"] if ref else {}).items()
            if evaluate.exact_value(record["fields"].get(key), value)
        )
        answers = {item["question_id"]: item for item in record["answers"]}
        answers_ok = sum(
            1
            for item in (ref["answers"] if ref else [])
            if (answer := answers.get(item["question_id"])) is not None
            and answer["answerable"] == item["answerable"]
            and evaluate.exact_value(answer["value"], item["value"])
            and set(answer["sources"]) == set(item["sources"])
        )
        validation = record["validation"]
        yield {
            "type": "document",
            "document_id": document_id,
            "document_title": analysis.document_title,
            "type_ok": bool(ref) and ref["document_type"] == record["document_type"],
            "fields_ok": fields_ok,
            "fields_total": len(ref["fields"]) if ref else 0,
            "validation_ok": bool(ref)
            and validation["status"] == ref["validation"]["status"]
            and set(validation["missing_fields"]) == set(ref["validation"]["missing_fields"])
            and set(validation["sources"]) == set(ref["validation"]["sources"]),
            "answers_ok": answers_ok,
            "answers_total": len(ref["answers"]) if ref else 0,
            "ms": round((time.perf_counter() - started) * 1000),
        }
    report = evaluate.evaluate(reference, {"version": RESULTS_VERSION, "documents": documents})
    yield {
        "type": "done",
        "documents": report["documents"],
        "questions": report["questions"],
        "field_accuracy_macro": report["field_accuracy_macro"],
        "validation_exact_match": report["validation_exact_match"],
        "question_exact_match": report["question_exact_match"],
        "errors": report["errors"][:20],
    }
