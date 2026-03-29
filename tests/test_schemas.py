"""Tests for JSON Schema definitions.

Verifies that:
- All expected schema files exist and are valid JSON Schema
- A valid sample document passes validation against its schema
- An invalid sample document fails with meaningful errors
"""

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "src" / "aegis" / "schemas"

EXPECTED_SCHEMAS = [
    "plan_document",
    "build_report",
    "review_report",
    "planning_session",
    "readiness_result",
]


def load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / f"{name}.json"
    with open(path) as f:
        return json.load(f)


def make_valid_header(**overrides) -> dict:
    header = {
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
    header.update(overrides)
    return header


def make_valid_plan_document(**overrides) -> dict:
    doc = {
        **make_valid_header(document_type="PlanDocument", stage="plan"),
        "user_intent": "Build a CLI tool that converts CSV files to JSON format",
        "architecture": {
            "components": [
                {
                    "name": "csv_parser",
                    "responsibility": "Parse CSV input files",
                    "interfaces": {
                        "inputs": ["file_path: str"],
                        "outputs": ["parsed_rows: list[dict]"],
                    },
                    "dependencies": [],
                }
            ],
            "decisions": [
                {
                    "decision": "Use stdlib csv module",
                    "rationale": "No external dependencies needed for basic CSV",
                    "alternatives_considered": ["pandas"],
                    "trade_offs": "Less feature-rich but zero dependencies",
                }
            ],
        },
        "tasks": [
            {
                "task_id": "task-001",
                "description": "Implement CSV to JSON conversion",
                "acceptance_criteria": [
                    {
                        "criterion_id": "ac-001",
                        "description": "Converts a well-formed CSV file to JSON array",
                        "test_approach": "unit",
                    },
                    {
                        "criterion_id": "ac-002",
                        "description": "Skips malformed rows and logs warnings",
                        "test_approach": "unit",
                    },
                    {
                        "criterion_id": "ac-003",
                        "description": "Returns non-zero exit code on missing input file",
                        "test_approach": "integration",
                    },
                ],
                "dependencies": [],
                "estimated_complexity": "low",
                "target_files": ["src/converter.py"],
            }
        ],
        "scope_boundaries": {
            "in_scope": ["CSV to JSON conversion", "Error handling for malformed rows"],
            "out_of_scope": ["Streaming for large files", "JSON to CSV reverse conversion"],
        },
        "risks": [
            {
                "description": "CSV files with inconsistent delimiters may cause parsing failures",
                "likelihood": "medium",
                "mitigation": "Use csv.Sniffer to auto-detect delimiter",
            }
        ],
        "context": {
            "existing_architecture_ref": None,
            "relevant_previous_tasks": [],
            "known_constraints": ["Python 3.12+"],
        },
    }
    doc.update(overrides)
    return doc


class TestSchemaFilesExist:
    """Every expected schema file must exist and be loadable."""

    @pytest.mark.parametrize("schema_name", EXPECTED_SCHEMAS)
    def test_schema_file_exists(self, schema_name):
        path = SCHEMAS_DIR / f"{schema_name}.json"
        assert path.exists(), f"Schema file missing: {path}"

    @pytest.mark.parametrize("schema_name", EXPECTED_SCHEMAS)
    def test_schema_is_valid_json(self, schema_name):
        schema = load_schema(schema_name)
        assert isinstance(schema, dict)
        assert "$schema" in schema, "Schema must declare its JSON Schema draft"


class TestSchemaIsValidJsonSchema:
    """Each schema must itself be a valid JSON Schema document."""

    @pytest.mark.parametrize("schema_name", EXPECTED_SCHEMAS)
    def test_schema_validates_as_json_schema(self, schema_name):
        schema = load_schema(schema_name)
        jsonschema.Draft202012Validator.check_schema(schema)


class TestPlanDocumentValidation:
    """The PlanDocument schema correctly accepts valid and rejects invalid documents."""

    @pytest.fixture
    def schema(self):
        return load_schema("plan_document")

    @pytest.fixture
    def validator(self, schema):
        return jsonschema.Draft202012Validator(schema)

    def test_valid_plan_document_passes(self, validator):
        doc = make_valid_plan_document()
        validator.validate(doc)

    def test_missing_tasks_field_fails(self, validator):
        doc = make_valid_plan_document()
        del doc["tasks"]
        errors = list(validator.iter_errors(doc))
        assert len(errors) > 0
        error_messages = [e.message for e in errors]
        assert any("tasks" in msg for msg in error_messages), (
            f"Expected 'tasks' mentioned in error messages, got: {error_messages}"
        )

    def test_missing_user_intent_fails(self, validator):
        doc = make_valid_plan_document()
        del doc["user_intent"]
        errors = list(validator.iter_errors(doc))
        assert len(errors) > 0

    def test_missing_scope_boundaries_fails(self, validator):
        doc = make_valid_plan_document()
        del doc["scope_boundaries"]
        errors = list(validator.iter_errors(doc))
        assert len(errors) > 0

    def test_empty_tasks_array_is_valid_json(self, validator):
        doc = make_valid_plan_document(tasks=[])
        validator.validate(doc)

    def test_task_missing_acceptance_criteria_fails(self, validator):
        doc = make_valid_plan_document()
        del doc["tasks"][0]["acceptance_criteria"]
        errors = list(validator.iter_errors(doc))
        assert len(errors) > 0

    def test_invalid_stage_value_fails(self, validator):
        doc = make_valid_plan_document()
        doc["stage"] = "invalid_stage"
        errors = list(validator.iter_errors(doc))
        assert len(errors) > 0

    def test_invalid_status_value_fails(self, validator):
        doc = make_valid_plan_document()
        doc["status"] = "nonexistent"
        errors = list(validator.iter_errors(doc))
        assert len(errors) > 0

    def test_additional_properties_allowed(self, validator):
        doc = make_valid_plan_document()
        doc["custom_field"] = "should not cause validation failure"
        validator.validate(doc)


class TestBuildReportSchemaExists:
    """Basic existence and validity checks for BuildReport schema."""

    @pytest.fixture
    def schema(self):
        return load_schema("build_report")

    @pytest.fixture
    def validator(self, schema):
        return jsonschema.Draft202012Validator(schema)

    def test_schema_has_required_fields(self, schema):
        assert "required" in schema or "properties" in schema


class TestCLIEntryPoint:
    """The aegis CLI is accessible and shows help."""

    def test_aegis_help(self):
        from click.testing import CliRunner
        from aegis.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Aegis" in result.output

    def test_aegis_version(self):
        from click.testing import CliRunner
        from aegis.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
