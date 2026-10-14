"""Пакетная обработка набора документов и сборка results.json."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from paragraf.models import Analysis
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


def _analyze(
    pipeline: Pipeline, root: Path, entry: dict[str, Any], source: str, problems: list[str]
) -> Analysis:
    """Разбирает документ и не даёт одному плохому файлу сорвать весь прогон.

    Сначала читается файл выбранного вида, при ошибке второй. Если не удалось
    прочитать ни один, в результат попадает пустая карточка нужного типа:
    формат results.json остаётся верным, а остальные документы не теряются.
    """
    document_id = entry["document_id"]
    type_id = entry.get("document_type")
    order = [source, "pdf" if source == "image" else "image"]
    for kind in order:
        relative = entry.get(kind)
        if not relative:
            continue
        try:
            analysis = pipeline.analyze((root / relative).read_bytes(), type_id).analysis
        except Exception as error:  # один файл не должен останавливать весь набор
            problems.append(f"{document_id}: {relative} не прочитан ({type(error).__name__})")
            continue
        if analysis.supported:
            return analysis
        problems.append(f"{document_id}: тип документа не определён")
    if type_id and type_id in pipeline.registry:
        problems.append(f"{document_id}: записана пустая карточка")
        return pipeline.empty(type_id)
    raise ValueError(f"{document_id}: документ не прочитан, а тип в манифесте не указан")


def document_record(
    pipeline: Pipeline, document_id: str, analysis: Analysis, questions: list[dict[str, str]]
) -> dict[str, Any]:
    """Запись одного документа в формате results.json: карточка, проверка, ответы."""
    answers = []
    for item in questions:
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
    return {
        "document_id": document_id,
        "document_type": analysis.document_type,
        "fields": analysis.card(),
        "validation": analysis.validation.model_dump(),
        "answers": answers,
    }


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
    problems: list[str] = []
    for entry in load_manifest(manifest):
        document_id = entry["document_id"]
        analysis = _analyze(pipeline, root, entry, source, problems)
        documents.append(
            document_record(pipeline, document_id, analysis, asked.get(document_id, []))
        )
        if progress:
            progress(document_id)
    if problems and progress:
        for line in problems:
            progress(f"ВНИМАНИЕ: {line}")
    return {"version": RESULTS_VERSION, "documents": documents}
