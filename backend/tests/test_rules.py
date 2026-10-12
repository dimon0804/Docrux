import pytest

from paragraf.doctypes import DocType, DocTypeRegistry
from paragraf.models import FieldValue
from paragraf.rules.kb import RuleBook
from paragraf.rules.validate import validate


def test_rulebook_has_all_points(rulebook: RuleBook):
    assert len(rulebook) == 30
    assert "1.3" in rulebook
    assert "сотрудник деканата" in rulebook.get("1.3").text
    assert rulebook.get("3.2").section == "Справка об обучении"


def test_rulebook_rejects_text_without_points():
    with pytest.raises(ValueError):
        RuleBook.parse("# Заголовок\n\nПросто текст.")


def test_every_field_rule_exists_in_rulebook(registry: DocTypeRegistry, rulebook: RuleBook):
    for doc_type in registry:
        for field in doc_type.fields:
            assert field.rule in rulebook, f"{doc_type.id}.{field.key}: нет пункта {field.rule}"


def _card(doc_type: DocType, missing: set[str]) -> list[FieldValue]:
    fields = []
    for spec in doc_type.fields:
        found = spec.key not in missing
        value: str | bool = found if spec.is_mark else ("значение" if found else "не найдено")
        fields.append(
            FieldValue(
                key=spec.key,
                label=spec.label,
                type=spec.type,
                value=value,
                found=found,
                rule=spec.rule,
            )
        )
    return fields


def test_complete_document_cites_all_requirement_rules(registry: DocTypeRegistry):
    result = validate(
        registry.get("study_certificate"), _card(registry.get("study_certificate"), set())
    )
    assert result.status == "document_ok"
    assert result.missing_fields == []
    assert result.sources == ["rule:3.1", "rule:3.2", "rule:3.3"]


def test_incomplete_document_cites_only_violated_rules(registry: DocTypeRegistry):
    doc_type = registry.get("internship_certificate")
    result = validate(doc_type, _card(doc_type, {"grade", "seal_present"}))
    assert result.status == "missing_fields"
    assert set(result.missing_fields) == {"grade", "seal_present"}
    assert result.sources == ["rule:5.1", "rule:5.3"]


def test_leave_application_has_no_seal(registry: DocTypeRegistry):
    doc_type = registry.get("academic_leave_application")
    assert "seal_present" not in doc_type.keys
    assert validate(doc_type, _card(doc_type, set())).sources == ["rule:4.1", "rule:4.2"]


def test_new_type_needs_only_a_config_file(tmp_path, registry: DocTypeRegistry):
    (tmp_path / "library_card.yaml").write_text(
        """
id: library_card
title: Читательский билет
fields:
  - {key: reader_name, label: ФИО читателя, type: person, rule: "1.1"}
  - {key: card_number, label: Номер билета, type: code, rule: "1.1"}
""",
        encoding="utf-8",
    )
    loaded = DocTypeRegistry.load(tmp_path)
    assert loaded.get("library_card").keys == ["reader_name", "card_number"]


def test_broken_config_is_reported_with_file_name(tmp_path):
    (tmp_path / "bad.yaml").write_text(
        "id: bad\ntitle: Плохой\nfields:\n  - {key: a, label: А, type: mark, rule: '1.1'}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"bad\.yaml"):
        DocTypeRegistry.load(tmp_path)
