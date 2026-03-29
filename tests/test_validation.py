"""Tests for the schema validation layer.

Verifies that:
- A valid document passes validation
- An invalid document fails with specific field-level errors
- The validator auto-discovers the correct schema from document_type
- Unknown document types produce a failure result (not an exception)
- Malformed input produces a failure result (not an exception)
- The validator is stateless across calls
"""

import pytest

from aegis.validation.schema_validator import SchemaValidator


@pytest.fixture
def validator():
    return SchemaValidator()


def make_header(**overrides):
    base = {
        "aegis_version": "0.1.0",
        "document_type": "PlanDocument",
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "parent_document_id": None,
        "project_id": "test-project",
        "task_id": "task-001",
        "timestamp": "2026-03-29T12:00:00Z",
        "stage": "plan",
        "status": "approved",
    }
    base.update(overrides)
    return base


def make_valid_plan():
    return {
        **make_header(document_type="PlanDocument", stage="plan"),
        "user_intent": "Build a CSV to JSON converter CLI",
        "architecture": {
            "components": [
                {
                    "name": "converter",
                    "responsibility": "Convert CSV rows to JSON objects",
                    "interfaces": {"inputs": ["file_path: str"], "outputs": ["json: str"]},
                    "dependencies": [],
                }
            ],
            "decisions": [
                {
                    "decision": "Use stdlib csv",
                    "rationale": "No external deps needed",
                    "alternatives_considered": ["pandas"],
                    "trade_offs": "Less features but simpler",
                }
            ],
        },
        "tasks": [
            {
                "task_id": "t1",
                "description": "Implement converter",
                "acceptance_criteria": [
                    {"criterion_id": "ac1", "description": "Converts valid CSV", "test_approach": "unit"},
                    {"criterion_id": "ac2", "description": "Handles malformed rows", "test_approach": "unit"},
                    {"criterion_id": "ac3", "description": "Returns error on missing file", "test_approach": "integration"},
                ],
                "dependencies": [],
                "estimated_complexity": "low",
                "target_files": ["src/converter.py"],
            }
        ],
        "scope_boundaries": {
            "in_scope": ["CSV to JSON conversion"],
            "out_of_scope": ["JSON to CSV"],
        },
        "risks": [
            {"description": "Delimiter detection", "likelihood": "medium", "mitigation": "Use csv.Sniffer"}
        ],
        "context": {
            "existing_architecture_ref": None,
            "relevant_previous_tasks": [],
            "known_constraints": ["Python 3.12+"],
        },
    }


def make_valid_build_report():
    return {
        **make_header(document_type="BuildReport", stage="build"),
        "plan_document_id": "550e8400-e29b-41d4-a716-446655440001",
        "build_status": "success",
    }


def make_valid_review_report():
    return {
        **make_header(document_type="ReviewReport", stage="review"),
        "build_report_id": "550e8400-e29b-41d4-a716-446655440002",
        "verdict": "approved",
    }


class TestValidDocumentsPass:
    def test_valid_plan_document(self, validator):
        result = validator.validate(make_valid_plan())
        assert result.is_valid
        assert result.errors == []

    def test_valid_build_report(self, validator):
        result = validator.validate(make_valid_build_report())
        assert result.is_valid

    def test_valid_review_report(self, validator):
        result = validator.validate(make_valid_review_report())
        assert result.is_valid


class TestInvalidDocumentsFail:
    def test_missing_required_field_reports_field_name(self, validator):
        doc = make_valid_plan()
        del doc["tasks"]
        result = validator.validate(doc)
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("tasks" in err.message for err in result.errors)

    def test_wrong_type_reports_type_mismatch(self, validator):
        doc = make_valid_plan()
        doc["tasks"] = "not an array"
        result = validator.validate(doc)
        assert not result.is_valid
        assert any("type" in err.message.lower() or "array" in err.message.lower() for err in result.errors)

    def test_invalid_enum_value_fails(self, validator):
        doc = make_valid_plan()
        doc["stage"] = "nonexistent"
        result = validator.validate(doc)
        assert not result.is_valid

    def test_multiple_errors_all_reported(self, validator):
        doc = make_valid_plan()
        del doc["tasks"]
        del doc["user_intent"]
        result = validator.validate(doc)
        assert not result.is_valid
        assert len(result.errors) >= 2


class TestAutoDiscovery:
    def test_discovers_plan_document_schema(self, validator):
        doc = make_valid_plan()
        result = validator.validate(doc)
        assert result.is_valid
        assert result.schema_used == "plan_document"

    def test_discovers_build_report_schema(self, validator):
        doc = make_valid_build_report()
        result = validator.validate(doc)
        assert result.is_valid
        assert result.schema_used == "build_report"

    def test_discovers_review_report_schema(self, validator):
        doc = make_valid_review_report()
        result = validator.validate(doc)
        assert result.is_valid
        assert result.schema_used == "review_report"


class TestEdgeCases:
    def test_unknown_document_type_returns_failure(self, validator):
        doc = make_header(document_type="UnknownType")
        result = validator.validate(doc)
        assert not result.is_valid
        assert any("unknown" in err.message.lower() or "schema" in err.message.lower() for err in result.errors)

    def test_missing_document_type_returns_failure(self, validator):
        doc = {"some_field": "some_value"}
        result = validator.validate(doc)
        assert not result.is_valid

    def test_none_input_returns_failure(self, validator):
        result = validator.validate(None)
        assert not result.is_valid

    def test_empty_dict_returns_failure(self, validator):
        result = validator.validate({})
        assert not result.is_valid

    def test_string_input_returns_failure(self, validator):
        result = validator.validate("not a dict")
        assert not result.is_valid


class TestStatelessness:
    def test_failed_validation_does_not_affect_next_call(self, validator):
        bad_doc = make_valid_plan()
        del bad_doc["tasks"]
        result1 = validator.validate(bad_doc)
        assert not result1.is_valid

        good_doc = make_valid_plan()
        result2 = validator.validate(good_doc)
        assert result2.is_valid

    def test_two_validators_are_independent(self):
        v1 = SchemaValidator()
        v2 = SchemaValidator()
        result1 = v1.validate(make_valid_plan())
        result2 = v2.validate(make_valid_plan())
        assert result1.is_valid
        assert result2.is_valid
