"""Метрики для Prometheus: сколько документов, как быстро, сколько отказов.

Сервис работает в нескольких процессах uvicorn, поэтому prometheus_client
включается в многопроцессном режиме: каждый процесс пишет свои счётчики в
общую папку, а /metrics собирает их вместе. Папку задаёт переменная
PROMETHEUS_MULTIPROC_DIR; без неё метрики считаются в одном процессе.
Персональных данных в метках нет: только тип документа, итог и вид вопроса.
"""

from __future__ import annotations

import os
from pathlib import Path

_folder = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
if _folder:
    Path(_folder).mkdir(parents=True, exist_ok=True)

from prometheus_client import (  # noqa: E402  папка должна существовать до импорта
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

DOCUMENTS = Counter(
    "paragraf_documents_total",
    "Разобранные документы по типу и итогу проверки",
    ["document_type", "status"],
)
ANALYZE_SECONDS = Histogram(
    "paragraf_analyze_seconds",
    "Время разбора одного документа",
    buckets=(0.25, 0.5, 1, 1.5, 2, 3, 5, 8, 13, 21),
)
ANSWERS = Counter(
    "paragraf_answers_total",
    "Ответы на вопросы по виду вопроса и тому, нашёлся ли ответ",
    ["intent", "answerable"],
)
REJECTED = Counter(
    "paragraf_rejected_total",
    "Запросы, которые сервис отклонил, по причине",
    ["reason"],
)
WAITING = Gauge(
    "paragraf_ocr_waiting",
    "Запросы, ожидающие места в очереди распознавания",
    multiprocess_mode="livesum",
)


def render() -> tuple[bytes, str]:
    if _folder:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry), CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST
