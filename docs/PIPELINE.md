# Aegis — Pipeline Detail

## Full Pipeline Flow

```
                            ┌─────────────────┐
                            │   User Prompt    │
                            │  (raw, messy)    │
                            └────────┬─────────┘
                                     │
                       ┌─────────────▼──────────────┐
                       │     PLANNING ADVISOR       │
                       │  (collaborative session)   │
                       │                            │
                       │  - Asks clarifying Qs      │
                       │  - Proposes architecture   │
                       │  - Suggests scope          │◄──── Project Memory
                       │  - Drafts acceptance       │
                       │    criteria together        │
                       │  - Challenges assumptions  │
                       │                            │
                       │  User ←──→ Advisor         │
                       │  (back-and-forth dialogue) │
                       └─────────────┬──────────────┘
                                     │
                              DraftPlanDocument
                                     │
                            ┌────────▼─────────┐
                        ┌───│  READINESS GATE  │───┐
                        │   │  (mechanical      │   │
                        │   │   checklist)      │   │
                        │   └──────────────────┘   │
                      FAIL                        PASS
                        │                           │
                  (specific gaps              PlanDocument
                   fed back to                (validated)
                   advisor,                        │
                   conversation                    │
                   continues;                      │
                   max 3 rounds                    │
                   then escalate                   │
                   to human)                       │
                                                    ┌───────────┴──────────┐
                                                    │                      │
                                           ┌────────▼─────────┐  ┌────────▼─────────┐
                                           │   TEST AGENT     │  │   IMPL AGENT     │
                                           │   (sees ONLY     │  │   (sees ONLY     │
                                           │    spec)         │  │    spec)         │
                                           └────────┬─────────┘  └────────┬─────────┘
                                                    │                      │
                                               TestSuite              SourceCode
                                                    │                      │
                                           ┌────────▼─────────┐           │
                                       ┌───│ MUTATION TESTER  │───┐       │
                                       │   └──────────────────┘   │       │
                                   WEAK TESTS              ROBUST TESTS   │
                                       │                       │          │
                                  (loop: max 3            ┌────┴──────────┘
                                   rounds, then           │
                                   escalate to       ┌────▼────────────┐
                                   plan review)      │  TEST RUNNER    │
                                                     │  (isolated      │
                                                     │   Docker, no    │
                                                     │   LLM, just     │
                                                     │   stdout/stderr)│
                                                     └────────┬────────┘
                                                              │
                                                     ┌────────┴────────┐
                                                     │                 │
                                                   PASS             FAIL
                                                     │                 │
                                              BuildReport     ┌───────▼────────┐
                                              (success)       │  DEBUG AGENT   │
                                                              └───────┬────────┘
                                                                      │
                                                              (loop: max 3 attempts)
                                                                      │
                                                              ┌───────┴────────┐
                                                              │                │
                                                            FIXED          STUCK
                                                              │                │
                                                         (back to        ┌─────▼──────┐
                                                          test runner)   │ FRESH AGENT│
                                                                         │ (clean ctx)│
                                                                         └─────┬──────┘
                                                                               │
                                                                        (max 2 attempts)
                                                                               │
                                                                        ┌──────┴──────┐
                                                                        │             │
                                                                      FIXED       ESCALATE
                                                                        │          TO HUMAN
                                                                   (back to     (structured
                                                                    runner)      report)

                                              BuildReport ────────▶ REVIEW STAGE
                                              (success)

                                           ┌─────────────────────┐
                                           │   CODE REVIEWER     │
                                           │   (checklist from   │
                                           │    PlanDocument)    │
                                           └────────┬────────────┘
                                                    │
                                           ┌────────┴────────┐
                                           │                 │
                                        APPROVED       CHANGES NEEDED
                                           │                 │
                                     ReviewReport      (back to Build
                                     (success)          with specific
                                           │            feedback)
                                           │
                                    ┌──────▼──────────┐
                                    │ DOC GENERATOR   │
                                    │ + PROJECT       │
                                    │   MEMORY UPDATE │
                                    └─────────────────┘
```

## Stage 1: PLAN — Detailed Breakdown

### 1.1 Planning Advisor

**Purpose:** Collaboratively develop a complete, specific plan through conversation with the user. Acts as a senior developer mentoring a junior developer — never demands a perfect prompt, instead helps build one.

**Input:**
- Raw user prompt (natural language, any level of specificity)
- Project Memory (architecture docs, dependency maps, known issues, previous decisions)

**Behavior:**
The Planning Advisor engages in an interactive dialogue with the user. It does NOT passively wait for a perfect prompt. On receiving any input, it:

1. **Acknowledges what's clear** — Reflects back what it understood to confirm alignment.
2. **Identifies gaps** — Determines what's missing from the Readiness Checklist (see 1.2) and formulates targeted questions.
3. **Proposes, doesn't just ask** — Instead of "what architecture do you want?", it says "based on your description, I'd suggest X architecture because Y — does that align with your thinking, or did you have something else in mind?"
4. **Challenges assumptions** — If the user's idea has potential issues, the advisor raises them early: "This approach works, but be aware it means Z trade-off. Are you okay with that?"
5. **Manages scope proactively** — If the user's request is too large for one iteration, the advisor suggests how to split it and which piece to build first.
6. **Drafts incrementally** — As the conversation progresses, the advisor builds up a DraftPlanDocument piece by piece, confirming each section with the user.

**Session state:** The advisor maintains a running view of:
- Which Readiness Checklist items are satisfied
- Which items still need work
- The current DraftPlanDocument (updated after each exchange)

**When the advisor believes all checklist items are covered**, it presents the DraftPlanDocument to the user for final confirmation, then submits it to the Readiness Gate.

**Key design principle:** The advisor does the heavy lifting. A user can start with "I want a CLI tool that does something with CSV files" and the advisor will collaboratively refine that into a complete plan with architecture, acceptance criteria, and scope boundaries. The user provides intent and makes decisions; the advisor provides structure and specificity.

### 1.2 Readiness Gate

**Purpose:** Mechanical validation that the DraftPlanDocument meets minimum requirements before it can enter the Build stage. This is the "compiler" — but it validates the plan, not the user's prompt.

**Readiness Checklist (configurable per project):**

| Requirement | What it checks | Why it's required |
|------------|---------------|-------------------|
| Behavioral description | The plan describes what the feature/fix DOES, not just what it looks like | Prevents the Build stage from guessing intent |
| Input/output specification | Explicit I/O definitions or explicit "none" | Test Agent needs this to write meaningful tests |
| Testable acceptance criteria (min 3) | Each criterion has a measurable outcome, not a subjective quality | Mutation Tester needs mechanically verifiable criteria |
| Scope boundaries | Both in-scope AND out-of-scope items listed | Prevents scope creep during Build |
| Architecture decisions | New components/dependencies have rationale and alternatives considered | Prevents accidental complexity |
| Risk identification | At least one risk acknowledged | Forces consideration of what could go wrong |

**Validation is mechanical:** Each checklist item maps to a structural check on the JSON document. "Does the `acceptance_criteria` array have >= 3 items?" "Does each item have a non-empty `measurable_outcome` field?" "Is the `out_of_scope` array non-empty?" No LLM judgment — just schema and structural validation.

**On failure:** The gate returns the specific gaps (not a generic rejection) to the Planning Advisor. The advisor then continues the conversation with the user, focusing on the missing items. The user never sees the raw checklist failure — the advisor translates it into natural conversation.

**Loop guard:** Max 3 Readiness Gate attempts. If the plan still doesn't pass, escalate to the user with a structured report showing exactly which requirements aren't met and what the advisor has tried. This likely indicates the readiness checklist itself is misconfigured for the project type, not that the user's idea is bad.

### Planning Stage — What Changed and Why

The original design (Preprocessor → Prompt Compiler → Plan Agent → Plan Reviewer) had the hard gate at the INPUT to planning. This placed the entire burden on the user: "give me a complete, specific prompt or I reject it." This is backwards for several reasons:

1. **Users don't think in specs.** They think in vague intentions. The AI should help them get to specificity, not demand it.
2. **Rejection is demoralizing.** Being told "your prompt is incomplete" without help fixing it is the exact frustration that makes people abandon structured workflows.
3. **The AI is better at structuring than the user.** An LLM can take a vague idea and propose specific architecture, acceptance criteria, and scope far more efficiently than a human can write them from scratch.

The new design puts the gate at the OUTPUT. The user provides intent, the AI provides structure, and the gate ensures the result is complete before it reaches the Build stage. The human makes decisions; the AI does legwork; the gate enforces standards.

## Stage 2: BUILD — Detailed Breakdown

### 2.1 Test Agent

**Purpose:** Write test suites from the spec alone — adversarial to implementation.

**Input:** PlanDocument (specifically: acceptance criteria, API surface, expected behaviors).
**NOT provided:** Any implementation code, ever.

**Output:** TestSuite — executable test files targeting the acceptance criteria.

**Design principle:** Tests written from the spec will test what the code SHOULD do, not what the code DOES do. This is the key defense against false-positive tests.

### 2.2 Mutation Tester

**Purpose:** Verify that the test suite is actually capable of catching bugs.

**Process:**
1. Generate skeleton/stub code that matches the spec's interface
2. Introduce mutations (arithmetic operator swaps, boundary changes, deleted statements, negated conditionals)
3. Run the test suite against each mutant
4. Calculate mutation score: (killed mutants / total mutants)

**Threshold:** Configurable, default 80%. Below threshold = tests are too weak.

**Loop guard:** Max 3 rounds of test improvement. If mutation score stays below threshold, escalate to Plan Reviewer — the acceptance criteria may be too vague to write strong tests from.

**Tools:** `mutmut` (Python), `cargo-mutants` (Rust), `Stryker` (JavaScript/TypeScript).

### 2.3 Implementation Agent

**Purpose:** Write code that satisfies the spec.

**Input:** PlanDocument (architecture, task breakdown, acceptance criteria).
**NOT provided:** The test suite, ever.

**Output:** Source code files.

### 2.4 Test Runner

**Purpose:** Mechanically execute tests against code. Zero LLM involvement.

**Environment:** Isolated Docker container with:
- Language runtime and dependencies
- Test framework
- No network access (optional, configurable)
- Strict timeout

**Output:** Raw stdout/stderr + exit code. Nothing interpreted, nothing summarized. The raw output is what the Debug Agent receives.

### 2.5 Debug Agent

**Purpose:** Fix failing tests.

**Input:**
- PlanDocument (spec and acceptance criteria)
- Raw test output (stdout/stderr, exit code)
- Current source code

**NOT provided:** The test agent's reasoning or approach.

**Loop guard:** Max 3 fix attempts. Each attempt gets the updated test output. After 3 failures, the Debug Agent's context is considered polluted — escalate to Fresh Agent.

### 2.6 Fresh Agent (Escalation)

**Purpose:** Break circular reasoning by providing a clean perspective.

**Input:**
- PlanDocument
- TestSuite
- Raw failing test output
- Architecture documentation from Project Memory
- A structured summary of what was tried and failed (from the Debug Agent's loop)

**NOT provided:** The Debug Agent's code or reasoning. The Fresh Agent starts from scratch.

**Loop guard:** Max 2 attempts. After that, escalate to human with a structured FailureReport containing everything tried, all test outputs, and the agent's hypothesis about the root cause.

## Stage 3: REVIEW — Detailed Breakdown

### 3.1 Code Reviewer

**Purpose:** Final quality gate before code is accepted.

**Review checklist (derived from PlanDocument):**
- [ ] Each acceptance criterion is satisfied
- [ ] No undocumented dependencies introduced
- [ ] No existing interfaces modified without updating dependents
- [ ] Code style consistent with project conventions
- [ ] No obvious security concerns (hardcoded secrets, SQL injection, etc.)

**Output on approval:** ReviewReport (success) with quality notes.
**Output on rejection:** ReviewReport (changes_requested) with specific, actionable feedback routed back to Build stage.

### 3.2 Documentation Generator

**Purpose:** Update living project documentation.

**Updates:**
- Architecture overview (if new components added)
- API surface documentation
- Dependency map
- Test coverage report

### 3.3 Project Memory Update

**Purpose:** Append structured knowledge entries from this development cycle.

**Entries include:**
- What was built (linked to PlanDocument task IDs)
- What failed during building (with root causes)
- What decisions were made and why
- What bugs were encountered and how they were resolved
- Performance of each agent (for future optimization / fine-tuning data)
