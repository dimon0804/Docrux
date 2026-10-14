from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paragraf.api.app import create_app
from paragraf.pipeline import Pipeline
from paragraf.settings import Settings


@pytest.fixture(scope="module")
def client(settings: Settings, pipeline: Pipeline):
    with TestClient(create_app(settings, pipeline)) as test_client:
        yield test_client


def _analyze(client: TestClient, open_dir: Path, name: str) -> dict:
    path = open_dir / "documents" / f"{name}.pdf"
    response = client.post(
        "/api/analyze", files={"file": ("doc.pdf", path.read_bytes(), "application/pdf")}
    )
    assert response.status_code == 200
    return response.json()["analysis"]


def _card(analysis: dict) -> list[dict]:
    return [
        {"key": field["key"], "value": field["value"], "found": field["found"]}
        for field in analysis["fields"]
    ]


def _field(fields: list[dict], key: str) -> dict:
    return next(field for field in fields if field["key"] == key)


def test_empty_field_points_to_its_place(client: TestClient, open_dir: Path):
    analysis = _analyze(client, open_dir, "open-012")
    date = _field(analysis["fields"], "application_date")
    assert date["found"] is False and date["box"] is None
    hint = date["hint_box"]
    assert hint is not None
    # Место для даты правее метки, на одной строке с ней.
    leave_end = _field(analysis["fields"], "leave_end")["box"]
    assert hint["y"] > leave_end["y"]
    assert hint["x"] > 0.15 and hint["x"] + hint["w"] <= 1
    assert hint["w"] > 0.1 and 0 < hint["h"] < 0.05
    # У найденных полей подсказки нет.
    assert all(f["hint_box"] is None for f in analysis["fields"] if f["found"])


@pytest.mark.parametrize(
    ("name", "key"), [("open-003", "signature_present"), ("open-004", "seal_present")]
)
def test_missing_mark_points_to_its_place(client: TestClient, open_dir: Path, name, key):
    analysis = _analyze(client, open_dir, name)
    mark = _field(analysis["fields"], key)
    assert mark["value"] is False
    hint = mark["hint_box"]
    assert hint is not None and hint["y"] > 0.6
    assert hint["x"] >= 0 and hint["x"] + hint["w"] <= 1 and hint["y"] + hint["h"] <= 1


def test_hint_lands_on_the_right_page(client: TestClient, open_dir: Path):
    import pymupdf

    merged = pymupdf.open()
    merged.new_page().insert_text((72, 100), "Сопроводительный лист", fontsize=14)
    with pymupdf.open(open_dir / "documents" / "open-012.pdf") as source:
        merged.insert_pdf(source)
    response = client.post(
        "/api/analyze",
        files={"file": ("two.pdf", merged.tobytes(), "application/pdf")},
        data={"doc_type": "academic_leave_application"},
    )
    analysis = response.json()["analysis"]
    hint = _field(analysis["fields"], "application_date")["hint_box"]
    # Склеенный снимок вдвое выше: подсказка ниже границы страниц и вдвое ниже ростом.
    assert hint["y"] > analysis["page_breaks"][0]
    assert hint["h"] < 0.02


def test_clean_document_gives_no_advice(client: TestClient, open_dir: Path):
    assert _analyze(client, open_dir, "open-001")["advice"] == []


def test_check_normalizes_and_completes(client: TestClient, open_dir: Path):
    analysis = _analyze(client, open_dir, "open-012")
    assert analysis["validation"]["status"] == "missing_fields"
    card = _card(analysis)
    _field(card, "application_date").update(value="01.11.2026", found=True)

    response = client.post(
        "/api/check", json={"document_type": analysis["document_type"], "fields": card}
    )
    assert response.status_code == 200
    body = response.json()
    assert _field(body["fields"], "application_date")["value"] == "2026-11-01"
    assert body["validation"]["status"] == "document_ok"
    assert body["validation"]["missing_fields"] == []
    assert body["check"]["value"] == "document_ok"
    assert body["check"]["sources"] == body["validation"]["sources"]

    # Стёртое значение снова делает документ неполным.
    _field(card, "application_date").update(value="", found=False)
    _field(card, "signature_present").update(value=False, found=False)
    body = client.post(
        "/api/check", json={"document_type": analysis["document_type"], "fields": card}
    ).json()
    assert body["validation"]["missing_fields"] == ["application_date", "signature_present"]
    assert body["check"]["value"] == "missing_fields"
    assert body["check"]["highlight"] == ["application_date", "signature_present"]


def test_check_rejects_garbage_values(client: TestClient):
    fields = [
        {"key": "application_date", "value": "вчера", "found": True},
        {"key": "student_name", "value": "Иванову Ивану Ивановичу", "found": True},
        {"key": "course", "value": "третий", "found": True},
        {"key": "no_such_field", "value": "x", "found": True},
    ]
    body = client.post(
        "/api/check", json={"document_type": "academic_leave_application", "fields": fields}
    ).json()
    date = _field(body["fields"], "application_date")
    assert date == date | {"value": "не найдено", "found": False}
    assert _field(body["fields"], "student_name")["value"] == "Иванов Иван Иванович"
    assert _field(body["fields"], "course")["found"] is False
    assert all(field["key"] != "no_such_field" for field in body["fields"])


@pytest.mark.parametrize("doc_type", ["other", "../../etc/passwd", "unknown"])
def test_check_rejects_unknown_type(client: TestClient, doc_type: str):
    response = client.post("/api/check", json={"document_type": doc_type, "fields": []})
    assert response.status_code == 422
    assert response.json()["code"] == "unprocessable"


def test_ask_uses_corrected_values(client: TestClient):
    fields = [{"key": "application_date", "value": "1 ноября 2026 г.", "found": True}]
    response = client.post(
        "/api/ask",
        json={
            "document_type": "academic_leave_application",
            "fields": fields,
            "question": "Когда написано заявление?",
        },
    )
    assert response.status_code == 200
    assert response.json()["value"] == "2026-11-01"


def test_check_is_rate_limited(settings: Settings, pipeline: Pipeline):
    strict = settings.model_copy(update={"rate_limit_per_minute": 1})
    with TestClient(create_app(strict, pipeline)) as limited:
        body = {"document_type": "study_certificate", "fields": []}
        codes = [limited.post("/api/check", json=body).status_code for _ in range(2)]
    assert codes == [200, 429]
