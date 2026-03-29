# Aegis — Architecture

## Design Principles

Aegis applies SOLID principles not to application code, but to the development process itself.

| Principle | Application in Aegis |
|-----------|---------------------|
| **Single Responsibility** | Each agent has exactly one job. The Planning Advisor collaborates. The Readiness Gate validates. The test agent writes tests. The implementation agent implements. No agent holds two responsibilities. |
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
│ Planning      │   │ Test Agent    │   │ Code Reviewer │
│  Advisor      │   │ Mutation Test │   │ Doc Generator │
│ Readiness     │   │ Impl Agent    │   │ Memory Update │
│  Gate         │   │ Test Runner   │   │               │
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

The planning stage is **collaborative, not gatekeeping**. It behaves like a senior developer mentoring a junior developer — asking questions, proposing architecture, challenging assumptions, and helping the user refine their vision. The hard gate is at the OUTPUT (Readiness Gate), not the input.

Components:
1. **Planning Advisor** — An interactive, conversational agent that works with the user to develop a complete plan. It receives the raw user prompt and Project Memory, then engages in a back-and-forth dialogue: asking clarifying questions, proposing architectural approaches, suggesting scope boundaries, and drafting acceptance criteria collaboratively. The advisor does the heavy lifting — it doesn't demand the user provide a perfect prompt, it helps them build one.
2. **Readiness Gate** — A mechanical validation checkpoint at the output of the planning stage. Before a PlanDocument can be emitted and passed to the Build stage, the Readiness Gate verifies that specific requirements are met to a minimum level of specificity. If requirements are not met, the specific gaps are fed back to the Planning Advisor and the conversation continues. This is the "compiler" — but it validates the plan, not the user's prompt.

**Readiness Checklist (configurable per project):**
- [ ] Behavioral description: what the feature/fix does (not just what it looks like)
- [ ] Input/output specification (or explicit statement that there are none)
- [ ] At least N testable acceptance criteria (default N=3) with measurable outcomes
- [ ] Scope boundaries: what is in-scope AND what is explicitly out-of-scope
- [ ] Architecture decisions with rationale (if new components or dependencies are introduced)
- [ ] Risk identification (at least one risk considered, even if likelihood is low)

**Design rationale:** The previous design (Preprocessor → Prompt Compiler → Plan Agent → Plan Reviewer) placed the burden on the user to provide a complete prompt before any AI assistance. This is backwards — the AI should help the user get to completeness, not demand it upfront. The gate-at-output design means the user can start with a vague idea and the advisor will collaboratively refine it until the Readiness Gate is satisfied.

**Separation of concerns:** The Planning Advisor is conversational and warm (helps the user). The Readiness Gate is mechanical and strict (validates the output). The advisor's job is collaboration; the gate's job is enforcement. Neither does the other's job.

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
User ←──→ [Planning Advisor] ←──→ (interactive conversation)
                    │
                    ▼ (advisor believes requirements are met)
              DraftPlanDocument
                    │
                    ▼
             [Readiness Gate] ──── FAIL ──→ (gaps fed back to advisor,
                    │                        conversation continues)
                  PASS
                    │
              PlanDocument (validated)
                    │
              [Build Stage] ──▶ BuildReport
                    │
              [Review Stage] ──▶ ReviewReport
                    │
              [Project Memory]
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
| Mutation Tester → Test Agent | 3 rounds | Escalate to Planning Advisor (acceptance criteria may be ambiguous) |
| Test Runner → Debug Agent | 3 attempts | Escalate to Fresh Agent (clean context) |
| Fresh Agent → Test Runner | 2 attempts | Escalate to Human with structured "I'm stuck" report |
| Readiness Gate → Planning Advisor | 3 rounds | Escalate to Human (readiness requirements may be misconfigured) |

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
