"""Default sample interface documents for Sprint 1 CLI and tests."""

from __future__ import annotations


def sample_plan_document() -> dict:
    # Must satisfy both PlanDocument schema and ReadinessGate checklist.
    return {
        "aegis_version": "0.1.0",
        "document_type": "PlanDocument",
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "parent_document_id": None,
        "project_id": "aegis-sprint1-test",
        "task_id": "task-001",
        "timestamp": "2026-03-29T12:00:00Z",
        "stage": "plan",
        "status": "approved",
        "user_intent": "Build a CLI tool that converts CSV files to JSON format with error handling for malformed rows",
        "architecture": {
            "components": [
                {
                    "name": "csv_converter",
                    "responsibility": "Parse CSV input and produce JSON output",
                    "interfaces": {
                        "inputs": ["file_path: str"],
                        "outputs": ["json: str"],
                    },
                    "dependencies": [],
                }
            ],
            "decisions": [
                {
                    "decision": "Use the stdlib csv module",
                    "rationale": "Avoid extra dependencies during early skeleton development",
                    "alternatives_considered": ["pandas"],
                    "trade_offs": "Less sophisticated CSV inference but simpler runtime",
                }
            ],
        },
        "tasks": [
            {
                "task_id": "task-001",
                "description": "Implement CSV to JSON conversion with malformed-row handling",
                "acceptance_criteria": [
                    {
                        "criterion_id": "ac-001",
                        "description": "Converts a well-formed CSV file to a JSON array",
                        "test_approach": "unit",
                    },
                    {
                        "criterion_id": "ac-002",
                        "description": "Handles malformed rows by skipping them and recording an error",
                        "test_approach": "unit",
                    },
                    {
                        "criterion_id": "ac-003",
                        "description": "Returns a non-zero exit code when input file does not exist",
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
            "out_of_scope": ["Streaming for large files", "Reverse conversion (JSON to CSV)"],
        },
        "risks": [
            {
                "description": "CSV delimiter inconsistencies may cause parsing failures",
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


def sample_build_report(plan_document_id: str | None = None) -> dict:
    return {
        "aegis_version": "0.1.0",
        "document_type": "BuildReport",
        "document_id": "660e8400-e29b-41d4-a716-446655440000",
        "parent_document_id": None,
        "project_id": "aegis-sprint1-test",
        "task_id": "task-001",
        "timestamp": "2026-03-29T12:05:00Z",
        "stage": "build",
        "status": "approved",
        "plan_document_id": plan_document_id or "550e8400-e29b-41d4-a716-446655440000",
        "build_status": "success",
        # Optional fields left out intentionally for early skeleton.
    }


def sample_review_report(build_report_id: str | None = None) -> dict:
    return {
        "aegis_version": "0.1.0",
        "document_type": "ReviewReport",
        "document_id": "770e8400-e29b-41d4-a716-446655440000",
        "parent_document_id": None,
        "project_id": "aegis-sprint1-test",
        "task_id": "task-001",
        "timestamp": "2026-03-29T12:10:00Z",
        "stage": "review",
        "status": "approved",
        "build_report_id": build_report_id or "660e8400-e29b-41d4-a716-446655440000",
        "verdict": "approved",
        "checklist": [],
        "issues": [],
        "documentation_updates": {
            "architecture_changes": False,
            "new_components": [],
            "modified_interfaces": [],
            "new_dependencies": [],
        },
        "knowledge_entries": [],
    }

