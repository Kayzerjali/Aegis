"""Tests for the Readiness Gate.

Verifies that:
- A complete PlanDocument passes all readiness checks
- Each individual checklist item can independently cause failure
- Gaps are reported with specific, actionable descriptions
- The ReadinessResult document itself passes schema validation
- The minimum acceptance criteria count is configurable
"""

import pytest

from aegis.validation.readiness_gate import ReadinessGate
from aegis.validation.schema_validator import SchemaValidator


@pytest.fixture
def gate():
    return ReadinessGate()


@pytest.fixture
def schema_validator():
    return SchemaValidator()


def make_complete_plan():
    """A PlanDocument that satisfies all readiness requirements."""
    return {
        "aegis_version": "0.1.0",
        "document_type": "PlanDocument",
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "parent_document_id": None,
        "project_id": "test-project",
        "task_id": "task-001",
        "timestamp": "2026-03-29T12:00:00Z",
        "stage": "plan",
        "status": "approved",
        "user_intent": "Build a CLI tool that converts CSV files to JSON format with error handling for malformed rows",
        "architecture": {
            "components": [
                {
                    "name": "converter",
                    "responsibility": "Parse CSV and produce JSON output",
                    "interfaces": {"inputs": ["file_path: str"], "outputs": ["json: str"]},
                    "dependencies": [],
                }
            ],
            "decisions": [
                {
                    "decision": "Use stdlib csv module",
                    "rationale": "Zero external dependencies for basic CSV parsing",
                    "alternatives_considered": ["pandas"],
                    "trade_offs": "Less features but simpler",
                }
            ],
        },
        "tasks": [
            {
                "task_id": "t1",
                "description": "Implement CSV to JSON conversion",
                "acceptance_criteria": [
                    {"criterion_id": "ac1", "description": "Converts a well-formed CSV file to a JSON array", "test_approach": "unit"},
                    {"criterion_id": "ac2", "description": "Skips malformed rows and logs a warning per row", "test_approach": "unit"},
                    {"criterion_id": "ac3", "description": "Returns exit code 1 when input file does not exist", "test_approach": "integration"},
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
                "description": "CSV files with inconsistent delimiters may fail parsing",
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


class TestCompleteDocumentPasses:
    def test_complete_plan_passes_all_checks(self, gate):
        result = gate.evaluate(make_complete_plan())
        assert result.passed
        assert all(item["status"] == "met" for item in result.checklist)

    def test_result_has_no_gaps_summary(self, gate):
        result = gate.evaluate(make_complete_plan())
        assert result.gaps_summary is None


class TestBehavioralDescription:
    def test_missing_user_intent_fails(self, gate):
        plan = make_complete_plan()
        del plan["user_intent"]
        result = gate.evaluate(plan)
        assert not result.passed
        unmet = [c for c in result.checklist if c["requirement"] == "behavioral_description"]
        assert len(unmet) == 1
        assert unmet[0]["status"] == "unmet"

    def test_empty_user_intent_fails(self, gate):
        plan = make_complete_plan()
        plan["user_intent"] = ""
        result = gate.evaluate(plan)
        assert not result.passed

    def test_trivially_short_user_intent_fails(self, gate):
        plan = make_complete_plan()
        plan["user_intent"] = "do thing"
        result = gate.evaluate(plan)
        assert not result.passed


class TestAcceptanceCriteria:
    def test_fewer_than_minimum_criteria_fails(self, gate):
        plan = make_complete_plan()
        plan["tasks"][0]["acceptance_criteria"] = [
            {"criterion_id": "ac1", "description": "Does something", "test_approach": "unit"},
            {"criterion_id": "ac2", "description": "Does another thing", "test_approach": "unit"},
        ]
        result = gate.evaluate(plan)
        assert not result.passed
        unmet = [c for c in result.checklist if c["requirement"] == "acceptance_criteria"]
        assert unmet[0]["status"] == "unmet"

    def test_no_tasks_fails(self, gate):
        plan = make_complete_plan()
        plan["tasks"] = []
        result = gate.evaluate(plan)
        assert not result.passed

    def test_custom_minimum_criteria_count(self):
        gate = ReadinessGate(min_acceptance_criteria=1)
        plan = make_complete_plan()
        plan["tasks"][0]["acceptance_criteria"] = [
            {"criterion_id": "ac1", "description": "Does one thing", "test_approach": "unit"},
        ]
        result = gate.evaluate(plan)
        criteria_check = [c for c in result.checklist if c["requirement"] == "acceptance_criteria"]
        assert criteria_check[0]["status"] == "met"


class TestScopeBoundaries:
    def test_missing_scope_boundaries_fails(self, gate):
        plan = make_complete_plan()
        del plan["scope_boundaries"]
        result = gate.evaluate(plan)
        assert not result.passed

    def test_empty_out_of_scope_fails(self, gate):
        plan = make_complete_plan()
        plan["scope_boundaries"]["out_of_scope"] = []
        result = gate.evaluate(plan)
        assert not result.passed
        unmet = [c for c in result.checklist if c["requirement"] == "scope_boundaries"]
        assert unmet[0]["status"] == "unmet"

    def test_empty_in_scope_fails(self, gate):
        plan = make_complete_plan()
        plan["scope_boundaries"]["in_scope"] = []
        result = gate.evaluate(plan)
        assert not result.passed


class TestRiskIdentification:
    def test_missing_risks_fails(self, gate):
        plan = make_complete_plan()
        del plan["risks"]
        result = gate.evaluate(plan)
        assert not result.passed

    def test_empty_risks_array_fails(self, gate):
        plan = make_complete_plan()
        plan["risks"] = []
        result = gate.evaluate(plan)
        assert not result.passed
        unmet = [c for c in result.checklist if c["requirement"] == "risk_identification"]
        assert unmet[0]["status"] == "unmet"


class TestArchitectureDecisions:
    def test_missing_architecture_fails(self, gate):
        plan = make_complete_plan()
        del plan["architecture"]
        result = gate.evaluate(plan)
        assert not result.passed

    def test_empty_components_and_decisions_fails(self, gate):
        plan = make_complete_plan()
        plan["architecture"] = {"components": [], "decisions": []}
        result = gate.evaluate(plan)
        assert not result.passed


class TestInputOutputSpec:
    def test_tasks_with_no_description_fails(self, gate):
        plan = make_complete_plan()
        plan["tasks"][0]["description"] = ""
        result = gate.evaluate(plan)
        assert not result.passed

    def test_empty_tasks_fails_input_output_check(self, gate):
        plan = make_complete_plan()
        plan["tasks"] = []
        result = gate.evaluate(plan)
        io_check = [c for c in result.checklist if c["requirement"] == "input_output_spec"]
        assert len(io_check) == 1
        assert io_check[0]["status"] == "unmet"


class TestGapsSummary:
    def test_gaps_summary_present_on_failure(self, gate):
        plan = make_complete_plan()
        plan["risks"] = []
        plan["user_intent"] = ""
        result = gate.evaluate(plan)
        assert not result.passed
        assert result.gaps_summary is not None
        assert len(result.gaps_summary) > 0


class TestReadinessResultValidatesAgainstSchema:
    def test_passing_result_is_valid_document(self, gate, schema_validator):
        result = gate.evaluate(make_complete_plan())
        result_doc = result.to_document()
        validation = schema_validator.validate(result_doc)
        assert validation.is_valid, f"ReadinessResult failed schema validation: {validation.errors}"

    def test_failing_result_is_valid_document(self, gate, schema_validator):
        plan = make_complete_plan()
        plan["risks"] = []
        result = gate.evaluate(plan)
        result_doc = result.to_document()
        validation = schema_validator.validate(result_doc)
        assert validation.is_valid, f"ReadinessResult failed schema validation: {validation.errors}"
