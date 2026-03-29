# Aegis — Architecture

## Design Principles

Aegis applies SOLID principles not to application code, but to the development process itself.

| Principle | Application in Aegis |
|-----------|---------------------|
| **Single Responsibility** | Each agent has exactly one job. The preprocessor parses. The compiler validates. The planner plans. The test agent writes tests. The implementation agent implements. No agent holds two responsibilities. |
| **Open/Closed** | Each stage is a sub-pipeline, closed for modification but open for extension. Adding a security review agent to Stage 3 does not require changes to Stage 2. |
| **Liskov Substitution** | Any LLM (Claude, GPT, Gemini, fine-tuned local model) can fill any agent role as long as it consumes the correct input document and produces a conforming output document. Swap agents without changing the pipeline. |
| **Interface Segregation** | Stages communicate exclusively through typed interface documents. The test agent receives only the spec — never the implementation. The implementation agent receives only the spec — never the tests. Each agent gets exactly the interface it needs, nothing more. |
| **Dependency Inversion** | The pipeline orchestrator depends on abstract document schemas, not concrete agent implementations. It does not know or care whether Claude or Gemini is planning — it validates that a conforming PlanDocument was produced. |

## Three-Stage Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        DOCUMENTATION LAYER                          │
│  (Project Memory: updated as a side-effect of every stage)          │
└──────────────────────────────────────────────────────────────────────┘
        │                    │                    │
┌───────┴───────┐   ┌───────┴───────┐   ┌───────┴───────┐
│   STAGE 1     │   │   STAGE 2     │   │   STAGE 3     │
│    PLAN       │──▶│    BUILD      │──▶│    REVIEW      │
│               │   │               │   │               │
│ Preprocessor  │   │ Test Agent    │   │ Code Reviewer │
│ Compiler      │   │ Mutation Test │   │ Doc Generator │
│ Plan Agent    │   │ Impl Agent    │   │ Memory Update │
│ Plan Reviewer │   │ Test Runner   │   │               │
│               │   │ Debug Agent   │   │               │
│               │   │ Fresh Agent   │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
        │                    │                    │
   PlanDocument         BuildReport         ReviewReport
     (JSON)               (JSON)              (JSON)
```

### Stage 1: PLAN

**Input:** Raw user prompt (natural language, unstructured)
**Output:** PlanDocument (validated JSON)

Components:
1. **Prompt Preprocessor** — Parses messy human input into discrete, labeled concerns (feature request, bug fix, architecture question, clarification). This is a parser, not a validator. It structures; it does not judge.
2. **Prompt Compiler** — Validates each structured concern against a completeness checklist. Does the prompt specify inputs and outputs? Does it reference existing architecture? Is scope bounded to a single concern? Rejects with specific error messages, like a compiler.
3. **Plan Agent** — Generates architecture decisions, task breakdown, and acceptance criteria from the validated prompt. Consumes Project Memory for codebase context on iteration 2+.
4. **Plan Reviewer** — A separate agent that audits the plan. Does it solve what the user asked? Are edge cases addressed? Is scope realistic for one iteration? Can acceptance criteria be mechanically tested?

**Separation of concerns:** The preprocessor and compiler are distinct (Single Responsibility). The preprocessor handles structure ("I can't parse this"), the compiler handles completeness ("this is missing acceptance criteria"). Different failure modes, different error messages, different fixes.

### Stage 2: BUILD

**Input:** PlanDocument (validated JSON)
**Output:** BuildReport (validated JSON)

Components:
1. **Test Agent** — Reads ONLY the PlanDocument (never the implementation). Writes test suites from acceptance criteria and spec. This is the core of adversarial separation.
2. **Mutation Tester** — Automatically introduces small bugs (change `>` to `>=`, delete lines, swap variables) into stub/skeleton code and verifies that tests catch them. If tests pass with broken code, they are weak tests. Sends weak tests back to Test Agent.
3. **Implementation Agent** — Reads ONLY the PlanDocument (never the tests). Writes code to satisfy the spec.
4. **Test Runner** — A dumb process in an isolated Docker container. Executes tests against code. Captures stdout/stderr. Returns exit codes. No LLM interprets the results.
5. **Debug Agent** — On test failure, receives: the spec, the failing test output (raw), and the code. Attempts a fix.
6. **Fresh Agent (Escalation)** — After circuit breaker triggers, a completely new agent receives: the spec, the test suite, failing output, and architecture docs. It does NOT receive the previous agent's code or reasoning. Clean slate.

**Key invariant:** The test agent and implementation agent share the PlanDocument but NEVER share each other's output. This prevents context pollution — the root cause of false-positive verification loops.

### Stage 3: REVIEW

**Input:** BuildReport (validated JSON)
**Output:** ReviewReport (validated JSON)

Components:
1. **Code Reviewer** — Evaluates the implementation against a checklist derived from the PlanDocument. Does the code satisfy each acceptance criterion? Does it introduce undocumented dependencies? Does it modify existing interfaces without updating dependents?
2. **Documentation Generator** — Produces/updates living documentation: architecture overview, dependency maps, API surface, known issues.
3. **Project Memory Update** — Appends structured entries to the project knowledge base: what was built, what failed during building, what decisions were made, what bugs were encountered and how they were resolved.

### Documentation Layer (Cross-Cutting)

Documentation is not a final step — it is a side-effect of every stage:
- Stage 1 documents the plan and architectural decisions.
- Stage 2 documents what was built, what broke, what was tried, and what ultimately worked.
- Stage 3 documents the review findings and updates the canonical project memory.

The stack of interface documents (PlanDocument → BuildReport → ReviewReport) IS the project history. No separate "write docs" step needed for the audit trail.

## Interface Document Architecture

Stages are decoupled through strictly-typed JSON documents validated against JSON Schemas. This is the physical manifestation of the Interface Segregation Principle.

```
User ──▶ [Preprocessor] ──▶ StructuredPrompt
StructuredPrompt ──▶ [Compiler] ──▶ ValidatedPrompt | RejectionReport
ValidatedPrompt ──▶ [Plan Agent] ──▶ DraftPlan
DraftPlan ──▶ [Plan Reviewer] ──▶ PlanDocument | PlanRejection
PlanDocument ──▶ [Build Stage] ──▶ BuildReport
BuildReport ──▶ [Review Stage] ──▶ ReviewReport
ReviewReport ──▶ [Project Memory]
```

Each arrow is a typed contract. If the output doesn't conform to the schema, the producing agent is asked to retry (with the schema violation as feedback). This is mechanical validation — no LLM judgment involved.

Benefits:
- **Testability:** Each stage can be tested in isolation with mock documents.
- **Swappability:** Replace any agent without touching the pipeline (Liskov Substitution).
- **Auditability:** Every interface document is a checkpoint. A human can inspect any document to understand exactly what information flowed between stages.
- **Debuggability:** When something goes wrong, you know exactly which stage produced a bad document.

## Loop Guards and Escalation

Every loop in the pipeline has a circuit breaker:

| Loop | Max Iterations | Escalation Target |
|------|---------------|-------------------|
| Mutation Tester → Test Agent | 3 rounds | Escalate to Plan Reviewer (acceptance criteria may be ambiguous) |
| Test Runner → Debug Agent | 3 attempts | Escalate to Fresh Agent (clean context) |
| Fresh Agent → Test Runner | 2 attempts | Escalate to Human with structured "I'm stuck" report |
| Plan Reviewer → Plan Agent | 2 revisions | Escalate to Human with specific questions |

The "I'm stuck" report is not a vague failure message. It contains:
- What was attempted (each iteration's approach)
- What specifically failed (raw test output)
- The agent's hypothesis about WHY it's stuck
- The original spec and acceptance criteria for human review

## Model Agnosticism and Future Fine-Tuning

Aegis is designed so that any agent slot can be filled by any LLM:
- Frontier models (Claude, GPT, Gemini) for initial development
- Fine-tuned models (LoRA adapters on open-source bases) for specialized roles later

The architecture collects structured training data by default:
- Every PlanDocument is an example of "good planning" (if the build succeeds)
- Every test suite that passes mutation testing is an example of "good test writing"
- Every successful fix is an example of "good debugging"

After sufficient pipeline runs, this data can train specialized LoRA adapters for each agent role. The Liskov Substitution design means these can be hot-swapped without pipeline changes.
