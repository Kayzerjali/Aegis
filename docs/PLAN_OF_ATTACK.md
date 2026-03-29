# Aegis — Plan of Attack

> Practical execution plan. Each sprint is roughly 1 week with AI-assisted development.

## Prerequisites (before Sprint 1)

- [ ] Python 3.12+ installed and on PATH
- [ ] Docker Desktop installed and running (for isolated test runner)
- [ ] Gemini CLI installed and authenticated (`gemini auth login`)
- [ ] Claude Code installed and authenticated (`claude auth login`) — optional, can add later
- [ ] Cursor available for development (we use Cursor to build Aegis until Aegis can build itself)

---

## Sprint 1: Skeleton — "The pipeline runs, nothing is smart yet"

**Goal:** End-to-end pipeline that accepts a prompt and produces a PlanDocument, BuildReport, and ReviewReport — using mock agents that return canned responses. Proves the plumbing: state machine, schema validation, config system, CLI.

### Tasks

1. **Project scaffolding**
   - `pyproject.toml` with dependencies (langgraph, jsonschema, click, rich, docker)
   - Package structure matching IMPLEMENTATION.md
   - `aegis` CLI entry point via click

2. **JSON Schema definitions**
   - `schemas/plan_document.json`
   - `schemas/build_report.json`
   - `schemas/review_report.json`
   - `schemas/planning_session.json`
   - `schemas/readiness_result.json`
   - Based directly on INTERFACE_SCHEMAS.md

3. **Schema validation layer**
   - `validation/schema_validator.py` — validates any document against its schema
   - Returns structured errors on failure (which field, what's wrong)

4. **Readiness Gate**
   - `validation/readiness_gate.py` — mechanical checklist for PlanDocuments
   - Checks: behavioral description, I/O spec, acceptance criteria count, scope boundaries, architecture decisions, risk identification
   - Returns ReadinessResult document

5. **Config system**
   - `aegis init` creates `.aegis/` directory with default `config.toml`
   - `aegis config` reads/writes config values
   - Default engine assignments per role

6. **Engine adapter interface**
   - `engines/base.py` — abstract EngineAdapter class
   - `engines/mock.py` — mock adapter that returns canned responses (for testing)

7. **LangGraph pipeline skeleton**
   - `pipeline/graph.py` — top-level state machine
   - `pipeline/plan_stage.py` — Planning Advisor node (mock: returns a canned PlanDocument)
   - `pipeline/build_stage.py` — Build nodes (mock: returns a canned BuildReport)
   - `pipeline/review_stage.py` — Review nodes (mock: returns a canned ReviewReport)
   - State transitions enforced: Plan → Build → Review
   - Readiness Gate enforced between Plan and Build

8. **CLI commands (basic)**
   - `aegis init`
   - `aegis plan` (runs plan stage, outputs PlanDocument)
   - `aegis build` (runs build stage, outputs BuildReport)
   - `aegis status` (shows latest documents)

### Definition of Done
- `aegis init && aegis plan && aegis build` runs end-to-end with mock agents
- Every interface document passes schema validation
- Readiness Gate correctly rejects an incomplete PlanDocument and accepts a complete one

---

## Sprint 2: First Real Engine — "The advisor talks back"

**Goal:** Replace the mock planning advisor with a real Gemini CLI adapter. Interactive planning session produces a real PlanDocument through conversation.

### Tasks

1. **Gemini CLI adapter**
   - `engines/gemini_cli.py` — wraps `gemini -p` with JSON output
   - Handles errors, timeouts, auth failures gracefully
   - `is_available()` checks if gemini is installed and authenticated

2. **Planning Advisor agent**
   - `agents/planning_advisor.py` — system prompt, conversation management
   - Maintains readiness checklist state across turns
   - Presents DraftPlanDocument to user before submitting to Readiness Gate
   - On Readiness Gate failure, continues conversation targeting specific gaps

3. **Interactive `aegis plan`**
   - Terminal-based chat loop using `rich` for formatting
   - Shows readiness checklist progress as conversation evolves
   - User can type responses, advisor responds, repeat until gate passes
   - Saves PlanningSession transcript to `.aegis/documents/sessions/`

4. **Engine auto-detection**
   - On `aegis init`, detect which engines are installed and authenticated
   - Auto-configure default engine assignments based on what's available

### Definition of Done
- `aegis plan` starts a real conversation powered by Gemini CLI
- The advisor asks clarifying questions and proposes architecture
- A complete PlanDocument is produced and passes the Readiness Gate
- The session transcript is saved

---

## Sprint 3: Build Pipeline — "Tests and code from spec alone"

**Goal:** Real Test Agent and Implementation Agent, workspace isolation, Docker test runner. First end-to-end build cycle with actual code generation and testing.

### Tasks

1. **Workspace isolation**
   - `runners/workspace.py` — creates temp directories per agent
   - Test Agent workspace: only plan.json
   - Impl Agent workspace: only plan.json
   - Debug Agent workspace: plan.json + src/ + test_output.txt

2. **Test Agent**
   - `agents/test_agent.py` — system prompt that generates tests from spec only
   - Produces executable test files in the workspace
   - Output parsed and validated

3. **Implementation Agent**
   - `agents/impl_agent.py` — system prompt that generates code from spec only
   - Produces source files in the workspace
   - Output parsed and validated

4. **Docker test runner**
   - `runners/docker_runner.py` — builds a minimal container, copies tests + code, runs tests
   - Returns raw stdout, stderr, exit code
   - Configurable timeout
   - Language-specific base images (python:3.12-slim, rust:latest, node:lts)

5. **Build stage pipeline**
   - Wire up: Test Agent → Impl Agent → Test Runner
   - Handle pass/fail routing
   - Produce BuildReport (success or failure)

6. **`aegis build` with real agents**
   - Shows progress: which agent is running, what it produced
   - Displays test results clearly
   - Saves BuildReport to `.aegis/documents/builds/`

### Definition of Done
- Given a PlanDocument for a simple Python CLI tool:
  - Test Agent produces tests from spec alone (never sees implementation)
  - Impl Agent produces code from spec alone (never sees tests)
  - Docker runner executes tests against code
  - BuildReport is produced and passes schema validation
- Adversarial separation is enforced (verify: test workspace contains no source, impl workspace contains no tests)

---

## Sprint 4: Resilience — "It fixes itself, or it knows when to stop"

**Goal:** Debug Agent, Fresh Agent escalation, mutation testing, circuit breakers. The pipeline handles failures gracefully instead of looping forever.

### Tasks

1. **Debug Agent**
   - `agents/debug_agent.py` — receives spec + code + raw test output, attempts fix
   - Loop: fix → re-run tests → check result (max 3 attempts)

2. **Fresh Agent escalation**
   - `agents/fresh_agent.py` — clean context, receives summary of what was tried
   - Triggered after Debug Agent exhausts retries
   - Max 2 attempts before human escalation

3. **Human escalation report**
   - Structured FailureReport: what was tried, what failed, raw outputs, hypothesis
   - Displayed clearly in terminal on escalation

4. **Mutation testing integration**
   - `runners/mutation_runner.py` — wraps `mutmut` (Python) / `cargo-mutants` (Rust)
   - Generates mutants, runs test suite against each
   - Calculates mutation score
   - Loop: if below threshold, send back to Test Agent with feedback (max 3 rounds)
   - Escalates to Planning Advisor if acceptance criteria are too vague for strong tests

5. **Circuit breakers wired into LangGraph**
   - Conditional edges with iteration counters
   - Each loop tracks its count in the LangGraph state
   - Clean routing: retry → escalate → human

6. **Claude Code adapter** (second engine)
   - `engines/claude_cli.py` — wraps `claude -p --print --bare`
   - Configure high-value roles (planning advisor, impl agent) to use Claude

### Definition of Done
- Given a PlanDocument for a task that has a subtle bug:
  - Build runs, tests fail
  - Debug Agent attempts fix (up to 3 times)
  - If Debug Agent fails, Fresh Agent gets clean context
  - If Fresh Agent fails, user gets a structured FailureReport
  - At no point does the pipeline loop infinitely
- Mutation testing: weak tests are detected and sent back for improvement

---

## Sprint 5: Review + Memory — "It remembers and gets better"

**Goal:** Code review, documentation generation, project memory. Second build cycle can reference context from the first.

### Tasks

1. **Code Reviewer agent**
   - `agents/code_reviewer.py` — reviews against PlanDocument acceptance criteria
   - Produces ReviewReport with checklist, issues, verdict

2. **Documentation Generator agent**
   - `agents/doc_generator.py` — generates/updates project docs
   - Architecture overview, API surface, dependency map

3. **Project Memory**
   - `memory/store.py` — SQLite-backed storage
   - Stores: decisions, bugs, fixes, architecture state, agent performance
   - Queryable by task ID, component, date range

4. **Memory integration into Planning Advisor**
   - On `aegis plan`, advisor loads relevant project memory
   - References previous decisions, known issues, existing architecture
   - Second iteration plans are informed by first iteration context

5. **`aegis review` command**
   - Runs review pipeline on latest BuildReport
   - Displays review results, issues, and documentation updates

6. **`aegis history` and `aegis inspect` commands**
   - `aegis history` — show document chain for a task
   - `aegis inspect <id>` — pretty-print any interface document

### Definition of Done
- Full cycle: plan → build → review → memory update
- Second `aegis plan` session shows awareness of what was built in the first cycle
- `aegis history` shows the complete document chain
- Project memory contains structured entries from the build cycle

---

## Sprint 6: Validation — "Build something real with it"

**Goal:** Use Aegis to build a small but real project. Find and fix the rough edges.

### Candidate validation project
A Python CLI tool of moderate complexity — something with:
- Multiple modules
- Error handling edge cases
- File I/O
- Testable acceptance criteria

This is NOT Thoth or Eidolon yet. This is a smaller project to shake out Aegis bugs before tackling the hard projects.

### Expected outcomes
- Discover which agent prompts need refinement
- Find pipeline edge cases (agents producing unexpected output formats, schema mismatches)
- Measure: how many build cycles complete without human escalation?
- Measure: does mutation testing actually catch weak tests?
- Measure: does the Debug Agent actually fix real bugs?

---

## After Sprint 6

If Aegis can reliably build a small Python project:
- **Phase 3:** Use Aegis to build Thoth (Rust terminal multiplexer)
- **Phase 4:** Use Aegis to build Eidolon (GUI automation for agents)
- **Phase 5:** Fine-tune LoRA adapters from collected pipeline data

---

## Development Approach

Aegis itself is built using Cursor, following these principles manually until Aegis can enforce them:

1. **Plan before coding** — Each sprint has a clear definition of done.
2. **Test incrementally** — Each component is tested before integration.
3. **Commit working states** — Every passing state gets committed.
4. **One concern per commit** — Keep the git history clean and reviewable.

We use feature branches for each sprint, merged to main only when the sprint's definition of done is fully met.
