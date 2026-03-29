# Aegis — Sprint 1 Spec Sheet

> This document serves as the PlanDocument for Sprint 1.
> Format: Vision + Requirements + Constraints + Acceptance Criteria per stage.
> Implementation approach is left to the agent's judgment within these bounds.

## Project Context

Aegis is a CLI tool that orchestrates AI coding agents through a Plan → Build → Review pipeline. Sprint 1 builds the skeleton: the pipeline runs end-to-end with mock agents, and all inter-stage communication happens through schema-validated JSON documents. The Readiness Gate mechanically enforces plan quality before any code generation begins.

### Dependency Documents

The following documents in the `docs/` directory provide detailed context referenced by this spec. The agent should consult them as needed:

- **INTERFACE_SCHEMAS.md** — Complete JSON structure definitions for every interface document (PlanDocument, BuildReport, ReviewReport, PlanningSession, ReadinessResult). Includes all field names, types, nesting, and the common document header.
- **ARCHITECTURE.md** — Three-stage pipeline design, SOLID principles mapping, Readiness Gate checklist items, loop guard definitions.
- **VISION.md** — Why Aegis exists, what problems it solves, what it is NOT.
- **IMPLEMENTATION.md** — Project structure overview, engine adapter interface, workspace isolation design, CLI command list.

## Global Constraints

These apply to ALL stages in this sprint:

### Design Principles
- Follow **SOLID principles** throughout. Each module should have a single responsibility. Components should depend on abstractions, not concrete implementations. New functionality should be addable without modifying existing code.
- Design for **testability**. Every component should be testable in isolation with no external dependencies (no network, no filesystem side-effects in unit tests, no AI engines).
- Prefer **composition over inheritance** where reasonable.

### Testing
- Use **pytest** as the test framework.
- Tests live in a `tests/` directory at the project root, mirroring the source structure.
- Write tests that verify **behavior** (what the component does), not implementation (how it does it internally).

### Development Workflow Per Stage
Each stage follows this order:

1. **Scaffold** — Create the minimum structure needed for tests to be importable and runnable (even if they fail). For Stage 1 only, this includes creating the package itself.
2. **Write tests** — From the acceptance criteria. Tests should fail initially (red).
3. **Mutation test** — Run `mutmut` against any logic-bearing code to verify test quality. Target ≥80% mutation score. *Note: stages that are primarily data/config (Stage 1, Stage 4) may have limited mutatable code. Mutation testing is most valuable for Stages 2, 3, 5, 6.*
4. **Implement** — Write the minimum code to pass all tests (green).
5. **Verify** — Run full test suite. Confirm mutation score if applicable.
6. **Commit** — Commit the working state.

### Stage 1 Bootstrapping Exception
Stage 1 has a circular dependency: you can't test "pip install works" without the package existing. For Stage 1 only, the workflow is:
1. Create the package scaffolding (pyproject.toml, __init__.py, CLI stub, empty schema files)
2. Verify `pip install -e .` and `aegis --help` work
3. Write tests for schema validity and document validation behavior
4. Populate the schema files with real JSON Schema content
5. Verify tests pass

## Architecture Vision

Three stages connected by typed JSON documents. Each stage is a node (or subgraph) in a LangGraph state machine. Documents flow forward through the pipeline. The Readiness Gate sits between Plan and Build as a hard validation checkpoint.

All "intelligence" in Sprint 1 comes from mock agents returning canned responses. The value is proving the plumbing: state transitions, schema validation, document flow, and gate enforcement.

```
User ──▶ Plan Stage ──▶ [Readiness Gate] ──▶ Build Stage ──▶ Review Stage
              │              ▲    │                │               │
         PlanDocument   FAIL │    │ PASS      BuildReport    ReviewReport
                             └────┘
```

---

## Stage 1: Project Foundation

### Vision
Establish the Python package so that all subsequent stages have a home. The package should be installable in development mode and expose an `aegis` CLI entry point, even if it only prints help text initially. JSON Schema files define the contracts that everything else depends on -- they are the "types" of the system.

### Requirements
- A Python package installable via `pip install -e .`
- An `aegis` CLI entry point accessible from the terminal
- JSON Schema definitions for every interface document type defined in INTERFACE_SCHEMAS.md: PlanDocument, BuildReport, ReviewReport, PlanningSession, ReadinessResult
- Each schema must enforce the required fields and types from our spec while allowing documents to evolve (additional properties permitted)

### Constraints
- Python 3.12+ (user has 3.13)
- Use `pyproject.toml` (not setup.py)
- Use `click` for CLI framework
- Schemas must be JSON Schema draft 2020-12 compatible
- Schemas are data files shipped with the package, not generated at runtime

### Acceptance Criteria
- `pip install -e .` succeeds without errors
- `aegis --help` prints a usage message
- Each schema file is valid JSON Schema (parseable, no schema errors)
- A hand-crafted valid PlanDocument validates successfully against the PlanDocument schema
- A hand-crafted invalid PlanDocument (missing required `tasks` field) fails validation with a meaningful error

---

## Stage 2: Schema Validation

### Vision
A validation module that any part of the pipeline can use to mechanically verify a document conforms to its schema. This is the foundation of document-driven architecture -- if a document doesn't pass validation, it doesn't enter the next stage. No LLM judgment involved, ever.

### Requirements
- Given a JSON document and a document type, validate the document against the corresponding schema
- Return a structured result indicating pass/fail with specific errors
- Automatically resolve which schema to use based on the `document_type` field in the document header
- Handle edge cases gracefully: unknown document types, malformed JSON, missing header

### Constraints
- Purely mechanical -- no LLM calls, no heuristics, no fuzzy matching
- Must not raise exceptions on bad input -- always return a result object
- Use the `jsonschema` library for validation
- Schema files are loaded from the package's schemas directory

### Acceptance Criteria
- A valid PlanDocument passes validation
- A PlanDocument missing a required field fails, and the error identifies which field
- A PlanDocument with a wrong type for a field fails, and the error identifies the type mismatch
- A document with an unknown `document_type` returns a failure result (not an exception)
- Completely malformed input (not valid JSON structure) returns a failure result
- The validator can be called repeatedly without state leaking between calls

---

## Stage 3: Readiness Gate

### Vision
The gatekeeper between Plan and Build. It checks whether a PlanDocument is specific enough for agents to write tests and code from. This is the "compiler" -- it doesn't judge quality, it checks structure. Is there a behavioral description? Are there enough testable acceptance criteria? Are scope boundaries defined?

This is distinct from schema validation (Stage 2). Schema validation checks "is this a valid JSON document?" The Readiness Gate checks "is this plan complete enough to build from?"

### Requirements
- Evaluate a PlanDocument against a readiness checklist
- Return a structured result showing which checklist items passed and which failed, with specific descriptions of what's missing
- The checklist items (from ARCHITECTURE.md):
  - Behavioral description exists and is non-trivial
  - Input/output specification exists
  - Minimum number of testable acceptance criteria met
  - Scope boundaries defined (both in-scope and out-of-scope)
  - Architecture decisions present (if new components are introduced)
  - At least one risk identified
- The minimum acceptance criteria count should be configurable

### Constraints
- Mostly mechanical checks (field presence, array length, non-empty strings)
- A few heuristic checks are acceptable (e.g., "behavioral description is more than N characters" to catch trivially short descriptions)
- The output must conform to the ReadinessResult schema (validated by Stage 2's validator)
- Must work independently of any AI engine

### Acceptance Criteria
- A complete PlanDocument passes all checks
- Removing the behavioral description causes failure with that specific gap identified
- Having only 2 acceptance criteria (below default threshold of 3) causes failure
- An empty `out_of_scope` array causes failure
- A PlanDocument with no risks causes failure
- The minimum criteria count can be overridden (e.g., set to 1 for simple tasks)
- The ReadinessResult document itself passes schema validation

---

## Stage 4: Configuration System

### Vision
Aegis needs project-level configuration: which engines to use for which roles, loop iteration limits, mutation testing thresholds. `aegis init` bootstraps a project directory, and the config loader makes these settings available to the pipeline.

### Requirements
- `aegis init` creates the project's `.aegis/` directory with default configuration and subdirectories for documents and memory
- A config loader that reads the configuration file and provides typed access to settings
- Default configuration covers: engine assignments per agent role, loop limits (debug retries, mutation rounds, readiness gate attempts), mutation score threshold
- Initialization is idempotent -- running `aegis init` on an already-initialized project preserves existing config

### Constraints
- Use TOML for configuration (human-readable, well-supported in Python)
- Config file lives at `.aegis/config.toml`
- Must not silently overwrite user's existing configuration

### Acceptance Criteria
- `aegis init` in an empty directory creates `.aegis/` with config file and subdirectories
- `aegis init` in an already-initialized directory does not overwrite existing config
- Config loader returns correct default values when using a fresh config
- Config values are accessible by key (e.g., engine for `test_agent` role, mutation threshold)
- Missing config file is handled gracefully (use defaults, warn user)

---

## Stage 5: Engine Adapter Interface

### Vision
The engine adapter is how Aegis talks to AI models. Sprint 1 only needs a mock adapter (real engines come in Sprint 2), but the interface must be designed so that real adapters can be dropped in later without changing any pipeline code. This is the Liskov Substitution boundary -- any adapter that implements the interface works.

### Requirements
- An abstract interface that all engine adapters must implement
- At minimum: a method for single-turn invocation (prompt in, response out), a method to check if the engine is available
- A structured response type that carries the model's output plus metadata (usage stats, model name)
- A mock adapter that returns configurable canned responses for testing
- The mock should be configurable per-role so different pipeline stages get different canned responses (plan stage gets a canned PlanDocument, build stage gets a canned BuildReport)

### Constraints
- The interface must not assume any specific AI provider's API shape
- The interface must support passing a working directory (for workspace isolation in later sprints)
- The mock adapter must be deterministic (same input → same output) for testability

### Acceptance Criteria
- The mock adapter conforms to the abstract interface
- Invoking the mock returns a response with content, usage metadata, and model name
- The mock can be configured with different responses for different roles
- The mock's `is_available()` returns True
- A second mock can be created with different configuration without affecting the first

---

## Stage 6: Pipeline State Machine

### Vision
The core of Aegis -- a LangGraph graph that moves through Plan → Readiness Gate → Build → Review. This is where the stages connect. In Sprint 1, each stage node calls a mock engine and validates the output. The Readiness Gate is a conditional edge that blocks progression if the PlanDocument isn't ready.

### Requirements
- A LangGraph state definition that tracks: current stage, documents produced so far, iteration counters for loops, and any errors encountered
- Stage nodes that invoke an engine adapter, receive a response, and validate the response against its schema
- The Readiness Gate as a conditional routing point: if the PlanDocument passes, route to Build; if it fails, route back to Plan (with gap information)
- The full pipeline produces a PlanDocument, BuildReport, and ReviewReport when run with valid mock responses
- Stage transitions are enforced -- Build cannot run without a validated PlanDocument

### Constraints
- Use LangGraph for the state machine (this is an architectural decision, ADR-006)
- Each stage node receives the pipeline state and returns an updated state
- Schema validation happens inside the pipeline (a stage that produces an invalid document should error, not silently pass garbage downstream)

### Acceptance Criteria
- Running the pipeline end-to-end with valid mock responses produces 3 documents (PlanDocument, BuildReport, ReviewReport)
- All 3 documents pass schema validation
- When the mock plan stage returns an incomplete PlanDocument, the Readiness Gate rejects it and the pipeline does not reach the Build stage
- Pipeline state correctly tracks which stage is current and which documents have been produced
- The pipeline can be invoked programmatically (not just via CLI) for testing

---

## Stage 7: CLI Integration

### Vision
Wire the pipeline to user-facing CLI commands. The user types `aegis plan`, the plan stage runs. They type `aegis build`, the build stage runs on the latest plan. `aegis status` shows what's been produced. This is the user interface for Sprint 1.

### Requirements
- `aegis plan` runs the plan stage, saves the PlanDocument to the project's document store
- `aegis build` loads the latest PlanDocument, runs it through the Readiness Gate, then runs the build stage, saves the BuildReport
- `aegis status` displays the most recent documents with their types, timestamps, and pass/fail status
- Commands provide clear feedback: what's happening, what was produced, any errors
- Commands fail gracefully with helpful messages when prerequisites aren't met

### Constraints
- Use `click` for CLI framework
- Use `rich` for terminal output formatting
- Documents are saved as JSON files in `.aegis/documents/` subdirectories
- Commands must work from any subdirectory within the project (find `.aegis/` by walking up)

### Acceptance Criteria
- `aegis plan` produces a PlanDocument file in `.aegis/documents/plans/`
- `aegis build` produces a BuildReport file in `.aegis/documents/builds/`
- `aegis status` shows at least the document type, timestamp, and status for recent documents
- Running `aegis build` before `aegis plan` gives a clear error message
- Running any command outside an initialized project gives a clear error message
- Running `aegis plan` then `aegis build` sequentially completes the pipeline

---

## Scope Boundaries

**In scope:**
- Pipeline skeleton with mock agents
- Schema validation (mechanical)
- Readiness Gate (mechanical)
- Config system with TOML
- CLI commands: init, plan, build, status
- All interface documents validated against schemas

**Out of scope:**
- Real AI engine integration (Sprint 2)
- Interactive planning conversation (Sprint 2)
- Workspace isolation / Docker test runner (Sprint 3)
- Debug Agent / Fresh Agent / circuit breakers (Sprint 4)
- Mutation testing of target project code (Sprint 4)
- Project Memory / SQLite (Sprint 5)
- Code review agent (Sprint 5)

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| LangGraph API learning curve causes delays | Medium | Start with the simplest possible graph (linear, one conditional edge), add complexity only as needed |
| JSON Schemas become too rigid as document formats evolve | Medium | Allow `additionalProperties` in all schemas initially; tighten only when stability is proven |
| Over-engineering the mock adapter delays real engine integration | Low | Mock only needs to return valid documents -- don't simulate conversation, streaming, or errors |

## Spec Format Rationale

### What the spec prescribes
- **Vision** — Why the component exists in the system (context)
- **Requirements** — What it must achieve, as outcomes
- **Constraints** — Hard boundaries: libraries, principles (SOLID), patterns, non-negotiables
- **Acceptance criteria** — Testable conditions for "done"
- **Dependency documents** — Other docs the agent should consult for detailed context
- **Global constraints** — Design principles, testing framework, development workflow
- **Bootstrapping exceptions** — Where the standard workflow doesn't cleanly apply and why

### What the spec does NOT prescribe
- Class names, method signatures, or function names
- File paths or module structure (beyond the top-level package)
- Internal data structures or algorithms
- Implementation order within a stage

### Why this format
AI agents reason best when given a well-defined problem space: clear goals, clear walls, but freedom to find the path. Prescriptive specs (write this class, this method, this file) reduce the agent to a typist. Vague specs ("build a validator") let the agent fill gaps with hallucinated assumptions. This format sits in the middle: the agent understands what success looks like and what rules it must follow, but chooses its own implementation approach.

This format will be the template for PlanDocuments that Aegis's Planning Advisor generates in production.
