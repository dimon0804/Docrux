from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from paragraf.api.app import create_app
from paragraf.api.security import RateLimiter
from paragraf.pipeline import Pipeline
from paragraf.settings import Settings


@pytest.fixture(scope="module")
def client(settings: Settings, pipeline: Pipeline):
    with TestClient(create_app(settings, pipeline)) as test_client:
        yield test_client


def _pdf(open_dir: Path, name: str) -> bytes:
    return (open_dir / "documents" / f"{name}.pdf").read_bytes()


def test_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_security_headers_are_set(client: TestClient):
    headers = client.get("/api/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["cache-control"] == "no-store"
    assert "x-request-id" in headers


def test_doc_types_and_rules(client: TestClient):
    types = client.get("/api/doc-types").json()
    assert {item["id"] for item in types} == {
        "study_certificate",
        "academic_leave_application",
        "internship_certificate",
    }
    rules = client.get("/api/rules").json()
    assert any(rule["number"] == "1.3" for rule in rules)


def test_analyze_with_question(client: TestClient, open_dir: Path):
    response = client.post(
        "/api/analyze",
        files={"file": ("doc.pdf", _pdf(open_dir, "open-002"), "application/pdf")},
        data={"doc_type": "study_certificate", "question": "Какова дата выдачи?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["validation"]["missing_fields"] == ["issue_date"]
    assert body["check"]["value"] == "missing_fields"
    assert body["answer"]["answerable"] is False
    assert body["image"].startswith("data:image/jpeg;base64,")


def test_analyze_detects_type_and_returns_boxes(client: TestClient, open_dir: Path):
    response = client.post(
        "/api/analyze",
        files={"file": ("doc.pdf", _pdf(open_dir, "open-021"), "application/pdf")},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["analysis"]["document_type"] == "internship_certificate"
    assert body["analysis"]["type_detected"] is True
    boxes = [field["box"] for field in body["analysis"]["fields"]]
    assert all(box is not None for box in boxes)
    assert all(0 <= box["x"] <= 1 and 0 <= box["y"] <= 1 for box in boxes)


def test_follow_up_question_needs_no_file(client: TestClient, open_dir: Path):
    first = client.post(
        "/api/analyze",
        files={"file": ("doc.pdf", _pdf(open_dir, "open-011"), "application/pdf")},
    ).json()
    fields = [
        {"key": field["key"], "value": field["value"], "found": field["found"]}
        for field in first["analysis"]["fields"]
    ]
    response = client.post(
        "/api/ask",
        json={
            "document_type": first["analysis"]["document_type"],
            "fields": fields,
            "question": "В какой группе учится студент?",
        },
    )
    assert response.status_code == 200
    assert response.json()["value"] == "ЖР-25-1"
    assert response.json()["sources"] == ["field:group"]


def test_unknown_question_is_refused(client: TestClient, open_dir: Path):
    response = client.post(
        "/api/analyze",
        files={"file": ("doc.pdf", _pdf(open_dir, "open-001"), "application/pdf")},
        data={"question": "Какой размер стипендии положен студенту?"},
    )
    answer = response.json()["answer"]
    assert answer["answerable"] is False
    assert answer["sources"] == []
    assert "нет информации" in answer["answer"]


@pytest.mark.parametrize(
    ("name", "payload", "mime"),
    [
        ("evil.pdf", b"MZ\x90\x00 this is not a pdf", "application/pdf"),
        ("page.png", b"<html><script>alert(1)</script></html>", "image/png"),
        ("empty.jpg", b"", "image/jpeg"),
        ("broken.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image/png"),
    ],
)
def test_bad_files_are_rejected(client: TestClient, name, payload, mime):
    response = client.post("/api/analyze", files={"file": (name, payload, mime)})
    assert response.status_code == 415
    assert response.json()["code"] == "unsupported"


def test_tiny_image_is_rejected(client: TestClient):
    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buffer, "PNG")
    response = client.post(
        "/api/analyze", files={"file": ("a.png", buffer.getvalue(), "image/png")}
    )
    assert response.status_code == 415


def test_oversized_upload_is_rejected(settings: Settings, pipeline: Pipeline):
    small = settings.model_copy(update={"max_upload_mb": 1})
    with TestClient(create_app(small, pipeline)) as limited:
        payload = b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024)
        response = limited.post("/api/analyze", files={"file": ("big.png", payload, "image/png")})
    assert response.status_code == 413


def test_unknown_doc_type_is_rejected(client: TestClient, open_dir: Path):
    response = client.post(
        "/api/analyze",
        files={"file": ("doc.pdf", _pdf(open_dir, "open-001"), "application/pdf")},
        data={"doc_type": "../../etc/passwd"},
    )
    assert response.status_code == 422


def test_ask_validates_payload(client: TestClient):
    response = client.post(
        "/api/ask",
        json={"document_type": "study_certificate", "fields": [], "question": "x" * 501},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "unprocessable"


def test_ask_ignores_forged_fields(client: TestClient):
    response = client.post(
        "/api/ask",
        json={
            "document_type": "study_certificate",
            "fields": [{"key": "no_such_field", "value": "<script>", "found": True}],
            "question": "Содержит ли документ все обязательные сведения?",
        },
    )
    assert response.status_code == 200
    assert response.json()["value"] == "missing_fields"


def test_errors_do_not_leak_internals(settings: Settings, pipeline: Pipeline, open_dir: Path):
    class Broken(Pipeline):
        def analyze(self, data, type_id=None):
            raise RuntimeError("секретный путь /srv/app/secret.py")

    broken = Broken(pipeline.registry, pipeline.rulebook, pipeline.engine, settings)
    with TestClient(create_app(settings, broken), raise_server_exceptions=False) as failing:
        response = failing.post(
            "/api/analyze",
            files={"file": ("doc.pdf", _pdf(open_dir, "open-001"), "application/pdf")},
        )
    assert response.status_code == 500
    assert "секретный" not in response.text
    assert response.json()["code"] == "internal"


def test_rate_limit_returns_429(settings: Settings, pipeline: Pipeline):
    strict = settings.model_copy(update={"rate_limit_per_minute": 2})
    with TestClient(create_app(strict, pipeline)) as limited:
        body = {"document_type": "study_certificate", "fields": [], "question": "Проверь документ"}
        codes = [limited.post("/api/ask", json=body).status_code for _ in range(4)]
    assert codes == [200, 200, 429, 429]


def test_rate_limiter_window_slides():
    limiter = RateLimiter(per_minute=2, window=60)
    assert limiter.allow("a", now=0)[0]
    assert limiter.allow("a", now=1)[0]
    allowed, retry_after = limiter.allow("a", now=2)
    assert not allowed and retry_after > 0
    assert limiter.allow("b", now=2)[0]
    assert limiter.allow("a", now=62)[0]


def _two_page_pdf(open_dir: Path, cover_first: bool = True) -> bytes:
    import pymupdf

    merged = pymupdf.open()
    cover = merged.new_page()
    cover.insert_text((72, 100), "Сопроводительный лист", fontsize=14)
    with pymupdf.open(open_dir / "documents" / "open-003.pdf") as source:
        merged.insert_pdf(source)
    if not cover_first:
        merged.move_page(0, 1)
    return merged.tobytes()


def test_multi_page_pdf_is_read_completely(client: TestClient, open_dir: Path):
    response = client.post(
        "/api/analyze",
        files={"file": ("two.pdf", _two_page_pdf(open_dir), "application/pdf")},
    )
    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["document_type"] == "study_certificate"
    assert analysis["quality"]["pages"] == 2
    assert len(analysis["page_breaks"]) == 1
    assert analysis["validation"]["missing_fields"] == ["signature_present"]
    name = next(field for field in analysis["fields"] if field["key"] == "student_name")
    assert name["value"] == "Жуков Андрей Дмитриевич"
    # Документ лежит на второй странице, значит и рамка поля ниже границы страниц.
    assert name["box"]["y"] > analysis["page_breaks"][0]
    seal = next(field for field in analysis["fields"] if field["key"] == "seal_present")
    assert seal["value"] is True and seal["box"]["y"] > analysis["page_breaks"][0]


def test_pdf_with_too_many_pages_is_rejected(client: TestClient):
    import pymupdf

    document = pymupdf.open()
    for _ in range(11):
        document.new_page()
    response = client.post(
        "/api/analyze", files={"file": ("long.pdf", document.tobytes(), "application/pdf")}
    )
    assert response.status_code == 415
    assert "страниц" in response.json()["detail"]
