# Aegis — Sprint 1 Spec Sheet

> This document serves as the PlanDocument for Sprint 1.
> It follows the same structure Aegis will eventually produce automatically.

## User Intent

Build the foundational skeleton of Aegis: a working CLI that runs a pipeline of mock agents through Plan → Build → Review stages, with schema-validated interface documents flowing between them and a Readiness Gate enforcing plan quality.

## Architecture

```
aegis (CLI entry point)
  │
  ├── aegis init ──→ creates .aegis/ directory with config.toml
  ├── aegis plan ──→ runs Plan stage ──→ produces PlanDocument
  ├── aegis build ──→ runs Build stage ──→ produces BuildReport
  └── aegis status ──→ displays latest documents
```

```
Plan Stage                    Build Stage                  Review Stage
┌──────────────────┐         ┌──────────────────┐        ┌──────────────────┐
│ Mock Advisor      │──JSON──▶│ Mock Test Agent   │──JSON─▶│ Mock Reviewer     │
│ Readiness Gate    │         │ Mock Impl Agent   │        │                  │
└──────────────────┘         │ Mock Test Runner  │        └──────────────────┘
                              └──────────────────┘
```

### Components

| Component | Responsibility | Dependencies |
|-----------|---------------|-------------|
| `schemas/` | JSON Schema definitions for all interface documents | None |
| `validation/schema_validator.py` | Validates any JSON document against its schema | `schemas/`, `jsonschema` |
| `validation/readiness_gate.py` | Checks PlanDocument meets readiness checklist | `validation/schema_validator.py` |
| `config/loader.py` | Loads/saves `.aegis/config.toml` | `tomli`/`tomli_w` |
| `config/defaults.py` | Default configuration values | None |
| `engines/base.py` | Abstract EngineAdapter interface | None |
| `engines/mock.py` | Mock adapter returning canned responses | `engines/base.py` |
| `pipeline/state.py` | LangGraph state definition | `langgraph` |
| `pipeline/plan_stage.py` | Plan stage graph nodes | `engines/`, `validation/` |
| `pipeline/build_stage.py` | Build stage graph nodes | `engines/`, `validation/` |
| `pipeline/review_stage.py` | Review stage graph nodes | `engines/`, `validation/` |
| `pipeline/graph.py` | Top-level pipeline wiring | `pipeline/*_stage.py` |
| `cli/main.py` | CLI entry point and command router | `click`, `pipeline/` |

## Development Stages

Each stage is a bounded unit of work with its own tests.

---

### Stage 1: Project Scaffolding + JSON Schemas

**What:** Create the Python package structure, `pyproject.toml`, and all JSON Schema definition files.

**Acceptance Criteria:**
1. `pip install -e .` succeeds and `aegis --help` prints usage
2. JSON Schema files exist for: PlanDocument, BuildReport, ReviewReport, PlanningSession, ReadinessResult
3. Each schema is itself valid JSON Schema (draft 2020-12)
4. A sample valid PlanDocument passes validation against its schema
5. A sample invalid PlanDocument (missing required field) fails validation

**Target Files:**
- `pyproject.toml`
- `src/aegis/__init__.py`
- `src/aegis/cli/__init__.py`, `src/aegis/cli/main.py`
- `src/aegis/schemas/plan_document.json`
- `src/aegis/schemas/build_report.json`
- `src/aegis/schemas/review_report.json`
- `src/aegis/schemas/planning_session.json`
- `src/aegis/schemas/readiness_result.json`

---

### Stage 2: Schema Validation Layer

**What:** Build the mechanical validation module that checks any JSON document against its corresponding schema.

**Acceptance Criteria:**
1. `SchemaValidator.validate(document, schema_name)` returns a `ValidationResult`
2. `ValidationResult.is_valid` is `True` for a conforming document
3. `ValidationResult.is_valid` is `False` for a non-conforming document
4. `ValidationResult.errors` contains specific field-level error messages on failure
5. Validator auto-discovers schema files from the `schemas/` directory by `document_type` field
6. Validating a document with an unknown `document_type` returns an error (not an exception)

**Target Files:**
- `src/aegis/validation/__init__.py`
- `src/aegis/validation/schema_validator.py`

---

### Stage 3: Readiness Gate

**What:** Build the mechanical checklist that validates a PlanDocument is complete enough for the Build stage.

**Acceptance Criteria:**
1. `ReadinessGate.evaluate(plan_document)` returns a `ReadinessResult` document
2. A PlanDocument with all required fields passes (result.passed == True)
3. A PlanDocument missing behavioral description fails with specific gap identified
4. A PlanDocument with fewer than 3 acceptance criteria fails with specific gap
5. A PlanDocument with empty `out_of_scope` fails with specific gap
6. A PlanDocument with no risks identified fails with specific gap
7. ReadinessResult itself passes schema validation
8. The minimum acceptance criteria count is configurable (default 3)

**Target Files:**
- `src/aegis/validation/readiness_gate.py`

---

### Stage 4: Config System

**What:** Build the configuration loader and `aegis init` command.

**Acceptance Criteria:**
1. `aegis init` creates a `.aegis/` directory in the current folder
2. `.aegis/config.toml` is created with sensible defaults
3. `.aegis/documents/`, `.aegis/memory/` subdirectories are created
4. `ConfigLoader.load(project_path)` returns a typed config object
5. Running `aegis init` twice does not overwrite existing config
6. Config includes: engine assignments per role, loop limits, mutation threshold

**Target Files:**
- `src/aegis/config/__init__.py`
- `src/aegis/config/defaults.py`
- `src/aegis/config/loader.py`
- Update `src/aegis/cli/main.py` with `init` command

---

### Stage 5: Engine Adapter Interface + Mock

**What:** Define the abstract engine interface and build a mock adapter for testing.

**Acceptance Criteria:**
1. `EngineAdapter` is an abstract base class with `invoke()`, `stream()`, `is_available()` methods
2. `MockEngine` implements `EngineAdapter` and returns configurable canned responses
3. `MockEngine.invoke(prompt, system_prompt, working_dir)` returns an `EngineResponse`
4. `EngineResponse` contains: `content`, `usage`, `model`, `raw` fields
5. `MockEngine.is_available()` always returns `True`
6. `MockEngine` can be configured with different responses per agent role (so plan stage mock returns a PlanDocument, build stage mock returns a BuildReport)

**Target Files:**
- `src/aegis/engines/__init__.py`
- `src/aegis/engines/base.py`
- `src/aegis/engines/mock.py`

---

### Stage 6: LangGraph Pipeline Skeleton

**What:** Wire up the three-stage pipeline as a LangGraph state machine with mock agents.

**Acceptance Criteria:**
1. Pipeline state includes: current stage, documents produced, iteration counts
2. Plan stage node invokes mock engine, produces PlanDocument, validates against schema
3. Readiness Gate runs between Plan and Build — rejects invalid PlanDocuments
4. Build stage node invokes mock engine, produces BuildReport, validates against schema
5. Review stage node invokes mock engine, produces ReviewReport, validates against schema
6. Running the full pipeline with valid mock responses produces 3 validated documents
7. Running with a mock that returns an incomplete PlanDocument triggers Readiness Gate failure

**Target Files:**
- `src/aegis/pipeline/__init__.py`
- `src/aegis/pipeline/state.py`
- `src/aegis/pipeline/plan_stage.py`
- `src/aegis/pipeline/build_stage.py`
- `src/aegis/pipeline/review_stage.py`
- `src/aegis/pipeline/graph.py`

---

### Stage 7: CLI Integration

**What:** Wire CLI commands to the pipeline. `aegis plan`, `aegis build`, `aegis status` all work.

**Acceptance Criteria:**
1. `aegis plan` runs the plan stage and saves PlanDocument to `.aegis/documents/plans/`
2. `aegis build` runs the build stage on the latest PlanDocument and saves BuildReport
3. `aegis status` displays the latest documents with timestamps and status
4. `aegis plan` fails gracefully if `aegis init` hasn't been run
5. `aegis build` fails gracefully if no PlanDocument exists
6. All commands display progress using `rich` formatting

**Target Files:**
- `src/aegis/cli/main.py` (update)
- `src/aegis/cli/plan.py`
- `src/aegis/cli/build.py`
- `src/aegis/cli/status.py`

---

## Scope Boundaries

**In scope:**
- Pipeline skeleton with mock agents
- Schema validation (mechanical)
- Readiness Gate (mechanical)
- Config system
- CLI commands (init, plan, build, status)
- All interface documents pass schema validation

**Out of scope (Sprint 1):**
- Real AI engine integration (Sprint 2)
- Interactive planning conversation (Sprint 2)
- Workspace isolation / Docker runner (Sprint 3)
- Debug Agent / Fresh Agent / circuit breakers (Sprint 4)
- Mutation testing of *target project* code (Sprint 4)
- Project Memory / SQLite (Sprint 5)
- Code review stage (Sprint 5)

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| LangGraph API changes or learning curve causes delays | Medium | Start with simplest possible graph, add complexity incrementally |
| JSON Schemas become too rigid for evolving document formats | Medium | Keep schemas loose initially (allow `additionalProperties`), tighten in later sprints |
| Mock agents mask integration issues | Low | Sprint 2 replaces mocks immediately; mocks are only for proving pipeline plumbing |

## Mutation Testing Setup (for Aegis's own tests)

We will use `mutmut` to verify our own test quality:

```bash
pip install mutmut
mutmut run --paths-to-mutate=src/aegis/ --tests-dir=tests/
mutmut results
```

Each stage's tests must achieve ≥80% mutation score before we move to implementation.
If tests are too weak, we strengthen them before writing any production code.
