"""Пакетная обработка набора документов и сборка results.json."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from paragraf.pipeline import Pipeline

RESULTS_VERSION = "1.0"


def load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["documents"] if isinstance(data, dict) else data


def load_questions(path: Path | None) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    if path is None:
        return grouped
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data["questions"] if isinstance(data, dict) else data:
        grouped[item["document_id"]].append(item)
    return grouped


def run_batch(
    pipeline: Pipeline,
    manifest: Path,
    questions: Path | None = None,
    source: str = "image",
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Прогоняет все документы манифеста и возвращает структуру results.json.

    ``source`` выбирает, какой файл документа читать: ``image`` или ``pdf``.
    Если нужного файла нет, берётся второй.
    """
    root = manifest.parent
    asked = load_questions(questions)
    documents = []
    for entry in load_manifest(manifest):
        document_id = entry["document_id"]
        other = "pdf" if source == "image" else "image"
        relative = entry.get(source) or entry.get(other)
        if not relative:
            raise ValueError(f"{document_id}: в манифесте нет пути к файлу")
        processed = pipeline.analyze((root / relative).read_bytes(), entry.get("document_type"))
        analysis = processed.analysis
        answers = []
        for item in asked.get(document_id, []):
            answer = pipeline.ask(analysis, item["question"])
            answers.append(
                {
                    "question_id": item["question_id"],
                    "answerable": answer.answerable,
                    "value": answer.value,
                    "answer": answer.answer,
                    "sources": answer.sources,
                }
            )
        documents.append(
            {
                "document_id": document_id,
                "document_type": analysis.document_type,
                "fields": analysis.card(),
                "validation": analysis.validation.model_dump(),
                "answers": answers,
            }
        )
        if progress:
            progress(document_id)
    return {"version": RESULTS_VERSION, "documents": documents}
