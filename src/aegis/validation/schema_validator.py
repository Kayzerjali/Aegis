"""Mechanical schema validation for Aegis interface documents.

Validates JSON documents against their corresponding JSON Schema definitions.
Auto-discovers which schema to use from the document's `document_type` field.
Never raises exceptions on bad input -- always returns a ValidationResult.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import jsonschema


# Maps document_type values to schema file names.
_DOCUMENT_TYPE_TO_SCHEMA = {
    "PlanDocument": "plan_document",
    "BuildReport": "build_report",
    "ReviewReport": "review_report",
    "PlanningSession": "planning_session",
    "ReadinessResult": "readiness_result",
}


@dataclass(frozen=True)
class ValidationError:
    """A single validation error with a human-readable message and the path to the offending field."""
    message: str
    path: str = ""


@dataclass(frozen=True)
class ValidationResult:
    """The outcome of validating a document against a schema."""
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    schema_used: str | None = None


class SchemaValidator:
    """Validates Aegis interface documents against JSON Schema definitions.

    Schemas are loaded once from the package's schemas directory and cached
    for the lifetime of the validator instance.
    """

    def __init__(self, schemas_dir: Path | None = None):
        self._schemas: dict[str, dict] = {}
        self._schemas_dir = schemas_dir or self._default_schemas_dir()
        self._load_schemas()

    def validate(self, document: object) -> ValidationResult:
        """Validate a document, auto-discovering its schema from the document_type header field."""
        if not isinstance(document, dict):
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError("Document must be a JSON object (dict)")],
            )

        doc_type = document.get("document_type")
        if doc_type is None:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError("Missing 'document_type' field in document header")],
            )

        schema_name = _DOCUMENT_TYPE_TO_SCHEMA.get(doc_type)
        if schema_name is None:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(f"Unknown document_type '{doc_type}': no schema found")],
            )

        schema = self._schemas.get(schema_name)
        if schema is None:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(f"Schema '{schema_name}' not loaded")],
            )

        return self._validate_against_schema(document, schema, schema_name)

    def _validate_against_schema(
        self, document: dict, schema: dict, schema_name: str
    ) -> ValidationResult:
        validator = jsonschema.Draft202012Validator(schema)
        raw_errors = list(validator.iter_errors(document))

        if not raw_errors:
            return ValidationResult(is_valid=True, schema_used=schema_name)

        errors = [
            ValidationError(
                message=err.message,
                path=err.json_path,
            )
            for err in raw_errors
        ]
        return ValidationResult(is_valid=False, errors=errors, schema_used=schema_name)

    def _load_schemas(self) -> None:
        if not self._schemas_dir.is_dir():
            return
        for schema_file in self._schemas_dir.glob("*.json"):
            try:
                with open(schema_file) as f:
                    self._schemas[schema_file.stem] = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

    @staticmethod
    def _default_schemas_dir() -> Path:
        return Path(__file__).resolve().parent.parent / "schemas"
