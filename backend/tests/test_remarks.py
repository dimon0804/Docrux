from __future__ import annotations

from datetime import date

from paragraf.models import FieldValue
from paragraf.rules.remarks import find_remarks

TODAY = date(2026, 10, 14)


def _fields(**values):
    return [
        FieldValue(
            key=key,
            label=key,
            type="date" if "date" in key or key.endswith(("_start", "_end")) else "text",
            value=value,
            found=True,
        )
        for key, value in values.items()
    ]


def test_clean_documents_of_the_open_set_have_no_remarks(pipeline, open_dir):
    for path in sorted((open_dir / "documents").glob("*.pdf")):
        analysis = pipeline.analyze(path.read_bytes()).analysis
        assert analysis.remarks == [], (path.name, analysis.remarks)


def test_period_ending_before_it_starts(registry):
    doc_type = registry.get("study_certificate")
    found = find_remarks(doc_type, _fields(study_start="2024-09-01", study_end="2023-06-30"), TODAY)
    assert len(found) == 1
    assert "раньше" in found[0].text
    assert found[0].fields == ["study_start", "study_end"]


def test_document_from_the_future_and_issued_before_study(registry):
    doc_type = registry.get("study_certificate")
    found = find_remarks(
        doc_type, _fields(study_start="2024-09-01", issue_date="2027-01-10"), TODAY
    )
    assert any("позже сегодняшнего дня" in remark.text for remark in found)
    found = find_remarks(
        doc_type, _fields(study_start="2024-09-01", issue_date="2023-01-10"), TODAY
    )
    assert [remark.text for remark in found] == ["Справка выдана раньше, чем началось обучение."]


def test_leave_specific_remarks(registry):
    doc_type = registry.get("academic_leave_application")
    found = find_remarks(
        doc_type,
        _fields(
            leave_start="2026-11-01",
            leave_end="2030-11-01",
            application_date="2026-12-01",
            course="9",
        ),
        TODAY,
    )
    texts = " ".join(remark.text for remark in found)
    assert "около 4 года" in texts
    assert "после даты начала отпуска" in texts
    assert "позже сегодняшнего дня" in texts
    assert "Курс «9»" in texts


def test_internship_specific_remarks(registry):
    doc_type = registry.get("internship_certificate")
    found = find_remarks(
        doc_type,
        _fields(
            internship_end="2026-07-15",
            issue_date="2026-07-01",
            student_name="Иванов Иван Иванович",
            supervisor_name="Иванов Иван Иванович",
            grade="супер",
        ),
        TODAY,
    )
    texts = " ".join(remark.text for remark in found)
    assert "до окончания практики" in texts
    assert "совпадают" in texts
    assert "не из обычного списка" in texts


def test_remarks_do_not_change_results_json(pipeline, open_dir):
    from paragraf.batch import run_batch

    manifest = open_dir / "documents.json"
    results = run_batch(pipeline, manifest, open_dir / "questions.json")
    assert all(
        set(doc) == {"document_id", "document_type", "fields", "validation", "answers"}
        for doc in results["documents"]
    )


def test_programme_code_is_checked_against_the_okso_levels(registry):
    doc_type = registry.get("study_certificate")
    assert find_remarks(doc_type, _fields(program="38.03.01 Экономика"), TODAY) == []
    level = find_remarks(doc_type, _fields(program="38.13.01 Экономика"), TODAY)
    assert "уровень образования" in level[0].text
    group = find_remarks(doc_type, _fields(program="77.03.01 Экономика"), TODAY)
    assert "укрупнённой группы" in group[0].text
