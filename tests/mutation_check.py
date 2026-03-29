"""Lightweight mutation testing for Windows environments.

Applies specific mutations to source code, runs the test suite, and verifies
that tests catch each mutation. Reports mutation score.

Usage: python tests/mutation_check.py
"""

import subprocess
import sys
import shutil
from pathlib import Path

TARGETS = {
    "schema_validator": {
        "source": Path("src/aegis/validation/schema_validator.py"),
        "tests": "tests/test_validation.py",
        "mutations": [
            {"name": "Remove dict type check", "find": "if not isinstance(document, dict):", "replace": "if False:"},
            {"name": "Remove document_type None check", "find": "if doc_type is None:", "replace": "if False:"},
            {"name": "Remove unknown schema_name check", "find": "if schema_name is None:", "replace": "if False:"},
            {"name": "Invert is_valid for valid documents", "find": "return ValidationResult(is_valid=True, schema_used=schema_name)", "replace": "return ValidationResult(is_valid=False, schema_used=schema_name)"},
            {"name": "Return empty errors on failure", "find": "return ValidationResult(is_valid=False, errors=errors, schema_used=schema_name)", "replace": "return ValidationResult(is_valid=False, errors=[], schema_used=schema_name)"},
            {"name": "Skip loading schemas", "find": "self._load_schemas()", "replace": "pass"},
        ],
    },
    "readiness_gate": {
        "source": Path("src/aegis/validation/readiness_gate.py"),
        "tests": "tests/test_readiness_gate.py",
        "mutations": [
            {"name": "Always pass behavioral description", "find": 'if isinstance(intent, str) and len(intent.strip()) >= _MIN_INTENT_LENGTH:', "replace": "if True:"},
            {"name": "Always pass acceptance criteria", "find": "if total_criteria < self._min_acceptance_criteria:", "replace": "if False:"},
            {"name": "Always pass scope boundaries (out_of_scope)", "find": "if not out_of_scope:", "replace": "if False:"},
            {"name": "Always pass risk identification", "find": "if not risks:", "replace": "if False:"},
            {"name": "Always pass architecture check", "find": "if not components and not decisions:", "replace": "if False:"},
            {"name": "Invert overall pass logic", "find": "passed = len(unmet) == 0", "replace": "passed = len(unmet) != 0"},
            {"name": "Suppress gaps summary on failure", "find": 'gaps_summary = "; ".join(gap_details)', "replace": "gaps_summary = None"},
            {"name": "Ignore empty tasks for input/output", "find": "if not tasks:", "replace": "if False:"},
        ],
    },
}

# Default target from CLI arg or run all
TARGET_NAME = sys.argv[1] if len(sys.argv) > 1 else None


def run_tests(test_file: str) -> bool:
    cmd = [sys.executable, "-m", "pytest", test_file, "-x", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def run_target(name: str, config: dict) -> tuple[int, int, list[str]]:
    source = config["source"]
    original = source.read_text()
    mutations = config["mutations"]
    killed = 0
    survived = 0
    survivors = []

    print(f"\n--- {name}: {len(mutations)} mutations against {source} ---\n")

    for i, mutation in enumerate(mutations, 1):
        if mutation["find"] not in original:
            print(f"  [{i}] SKIP - pattern not found: {mutation['name']}")
            continue

        mutated = original.replace(mutation["find"], mutation["replace"], 1)
        source.write_text(mutated)
        try:
            if run_tests(config["tests"]):
                survived += 1
                survivors.append(mutation["name"])
                print(f"  [{i}] SURVIVED - tests didn't catch: {mutation['name']}")
            else:
                killed += 1
                print(f"  [{i}] KILLED   - tests caught: {mutation['name']}")
        finally:
            source.write_text(original)

    return killed, survived, survivors


def main():
    targets = {TARGET_NAME: TARGETS[TARGET_NAME]} if TARGET_NAME else TARGETS
    total_killed = 0
    total_survived = 0
    all_survivors = []

    for name, config in targets.items():
        k, s, survivors = run_target(name, config)
        total_killed += k
        total_survived += s
        all_survivors.extend(survivors)

    total = total_killed + total_survived
    score = (total_killed / total * 100) if total > 0 else 0
    print(f"\nOverall mutation score: {total_killed}/{total} killed ({score:.0f}%)")

    if all_survivors:
        print(f"\nSurviving mutations:")
        for name in all_survivors:
            print(f"  - {name}")

    sys.exit(0 if score >= 80 else 1)


if __name__ == "__main__":
    main()
