"""Lightweight mutation testing for Windows environments.

Applies specific mutations to source code, runs the test suite, and verifies
that tests catch each mutation. Reports mutation score.

Usage: python tests/mutation_check.py
"""

import subprocess
import sys
import shutil
from pathlib import Path

SOURCE_FILE = Path("src/aegis/validation/schema_validator.py")
TEST_CMD = [sys.executable, "-m", "pytest", "tests/test_validation.py", "-x", "-q"]

MUTATIONS = [
    {
        "name": "Remove dict type check (should break edge case handling)",
        "find": "if not isinstance(document, dict):",
        "replace": "if False:",
    },
    {
        "name": "Remove document_type None check",
        "find": "if doc_type is None:",
        "replace": "if False:",
    },
    {
        "name": "Remove unknown schema_name check",
        "find": "if schema_name is None:",
        "replace": "if False:",
    },
    {
        "name": "Invert is_valid for valid documents",
        "find": "return ValidationResult(is_valid=True, schema_used=schema_name)",
        "replace": "return ValidationResult(is_valid=False, schema_used=schema_name)",
    },
    {
        "name": "Return empty errors on failure",
        "find": "return ValidationResult(is_valid=False, errors=errors, schema_used=schema_name)",
        "replace": "return ValidationResult(is_valid=False, errors=[], schema_used=schema_name)",
    },
    {
        "name": "Skip loading schemas",
        "find": "self._load_schemas()",
        "replace": "pass",
    },
]


def run_tests() -> bool:
    result = subprocess.run(TEST_CMD, capture_output=True, text=True)
    return result.returncode == 0


def main():
    original = SOURCE_FILE.read_text()
    killed = 0
    survived = 0
    errors = []

    print(f"Running {len(MUTATIONS)} mutations against {SOURCE_FILE}\n")

    for i, mutation in enumerate(MUTATIONS, 1):
        if mutation["find"] not in original:
            print(f"  [{i}] SKIP - pattern not found: {mutation['name']}")
            continue

        mutated = original.replace(mutation["find"], mutation["replace"], 1)
        SOURCE_FILE.write_text(mutated)

        try:
            tests_pass = run_tests()
            if tests_pass:
                survived += 1
                print(f"  [{i}] SURVIVED - tests didn't catch: {mutation['name']}")
                errors.append(mutation["name"])
            else:
                killed += 1
                print(f"  [{i}] KILLED   - tests caught: {mutation['name']}")
        finally:
            SOURCE_FILE.write_text(original)

    total = killed + survived
    score = (killed / total * 100) if total > 0 else 0
    print(f"\nMutation score: {killed}/{total} killed ({score:.0f}%)")

    if survived > 0:
        print(f"\nSurviving mutations (tests too weak):")
        for name in errors:
            print(f"  - {name}")

    sys.exit(0 if score >= 80 else 1)


if __name__ == "__main__":
    main()
