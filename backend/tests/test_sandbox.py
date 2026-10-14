from __future__ import annotations

import pytest

from paragraf import sandbox
from paragraf.pipeline import Pipeline

LEAVE = """
id: leave_short
title: Короткое заявление
fields:
  - key: who
    label: ФИО студента
    type: person
    rule: "9.1"
  - key: group
    label: Учебная группа
    type: code
    rule: "9.1"
  - key: written_on
    label: Дата заявления
    type: date
    rule: "9.2"
"""


def test_example_is_a_valid_type():
    doc_type = sandbox.parse(sandbox.EXAMPLE)
    assert doc_type.id == "sandbox_student_council_protocol"
    assert [field.key for field in doc_type.fields][:2] == ["meeting_date", "chairman"]


def test_sandbox_type_reads_a_real_document(pipeline: Pipeline, open_dir):
    doc_type = sandbox.parse(LEAVE)
    data = (open_dir / "documents" / "open-012.pdf").read_bytes()
    analysis = sandbox.run(pipeline, data, doc_type).analysis
    values = {field.key: field.value for field in analysis.fields}
    assert values["who"] == "Захаров Фёдор Дмитриевич"
    assert values["group"] == "ЖР-23-3"
    # В этом заявлении дата не вписана: поле пустое, проверка ссылается на свой пункт.
    assert values["written_on"] == "не найдено"
    assert analysis.validation.status == "missing_fields"
    assert analysis.validation.sources == ["rule:9.2"]
    assert analysis.supported is False


def test_sandbox_does_not_change_the_service_types(pipeline: Pipeline):
    before = [doc_type.id for doc_type in pipeline.registry]
    sandbox.parse(LEAVE)
    assert [doc_type.id for doc_type in pipeline.registry] == before


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("a: [1, 2", "YAML"),
        ("- просто список", "словарём"),
        ("id: x\ntitle: T\nfields: []", "хотя бы с одним полем"),
        (LEAVE + "freeform:\n  who:\n    patterns: ['(?P<value>.+)']\n", "freeform"),
        (
            LEAVE.replace(
                'rule: "9.1"\n  - key: group',
                "rule: \"9.1\"\n    patterns: ['(a+)+$']\n  - key: group",
                1,
            ),
            "patterns",
        ),
        ("base: &b {x: 1}\nother: *b\n", "Якоря"),
        (
            "id: Bad-Id\ntitle: T\nfields:\n  - key: a\n    label: A\n    rule: '1.1'\n",
            "Ошибка в описании",
        ),
        ("x" * (sandbox.MAX_CONFIG_CHARS + 1), "длиннее"),
    ],
)
def test_bad_descriptions_are_rejected_with_a_clear_reason(text: str, message: str):
    with pytest.raises(sandbox.SandboxError, match=message):
        sandbox.parse(text)


def test_too_many_fields_are_rejected():
    fields = "\n".join(
        f"  - key: f{i}\n    label: Поле {i}\n    rule: '1.1'"
        for i in range(sandbox.MAX_FIELDS + 1)
    )
    with pytest.raises(sandbox.SandboxError, match="Полей больше"):
        sandbox.parse(f"id: many\ntitle: Много\nfields:\n{fields}\n")


def test_sandbox_endpoint(open_dir):
    from fastapi.testclient import TestClient

    from paragraf.api.app import create_app
    from paragraf.settings import Settings

    settings = Settings(
        config_dir=open_dir.parents[1] / "config",
        pdf_text_layer="prefer",
        rate_limit_per_minute=1000,
    )
    with TestClient(create_app(settings)) as client:
        assert "student_council_protocol" in client.get("/api/sandbox/example").json()["text"]
        data = (open_dir / "documents" / "open-012.pdf").read_bytes()
        response = client.post(
            "/api/sandbox",
            files={"file": ("open-012.pdf", data, "application/pdf")},
            data={"config": LEAVE},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["analysis"]["document_type"] == "sandbox_leave_short"
        assert body["image"].startswith("data:image/jpeg;base64,")
        bad = client.post(
            "/api/sandbox",
            files={"file": ("open-012.pdf", data, "application/pdf")},
            data={"config": "base: &b {x: 1}"},
        )
        assert bad.status_code == 422
        assert "Якоря" in bad.json()["detail"]


@pytest.mark.parametrize(
    "text",
    [
        "[" * 7990,
        "x: " + "9" * 7900,
        "﻿&x a",
        "a: !!python/object:os.system 'echo'",
    ],
)
def test_hostile_yaml_is_rejected_cleanly(text: str):
    with pytest.raises(sandbox.SandboxError):
        sandbox.parse(text)


def test_composite_needs_exactly_two_keys():
    text = (
        LEAVE + "composites:\n  - label: Номер и дата\n    kind: number_and_date\n    keys: [who]\n"
    )
    with pytest.raises(sandbox.SandboxError, match="Ошибка в описании"):
        sandbox.parse(text)
