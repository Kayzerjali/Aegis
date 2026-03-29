# Aegis — Pipeline Detail

## Full Pipeline Flow

```
                            ┌─────────────────┐
                            │   User Prompt    │
                            │  (raw, messy)    │
                            └────────┬─────────┘
                                     │
                            ┌────────▼─────────┐
                            │  PREPROCESSOR    │
                            │  Parse & label   │
                            └────────┬─────────┘
                                     │
                            StructuredPrompt
                                     │
                            ┌────────▼─────────┐
                        ┌───│  PROMPT COMPILER  │───┐
                        │   │  Validate         │   │
                     REJECT └──────────────────┘  ACCEPT
                        │                           │
               RejectionReport              ValidatedPrompt
               (back to user                        │
                with specific              ┌────────▼─────────┐
                error messages)            │   PLAN AGENT     │
                                           │   + Project      │
                                           │     Memory       │
                                           └────────┬─────────┘
                                                    │
                                               DraftPlan
                                                    │
                                           ┌────────▼─────────┐
                                       ┌───│  PLAN REVIEWER   │───┐
                                       │   └──────────────────┘   │
                                    REJECT                      APPROVE
                                       │                           │
                                  (loop: max 2              PlanDocument
                                   revisions,               (validated)
                                   then escalate                │
                                   to human)                    │
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

### 1.1 Prompt Preprocessor

**Purpose:** Transform unstructured human input into labeled, discrete units.

**Input:** Raw string (user's natural language prompt, possibly rambling, multi-concern, or ambiguous).

**Processing:**
- Segment the input into discrete concerns using NLP/LLM classification
- Label each segment: `feature_request`, `bug_report`, `architecture_question`, `clarification`, `refinement`
- Extract entities: file references, function names, technology mentions
- Flag contradictions within the input

**Output:** StructuredPrompt JSON — an array of labeled, segmented concerns with extracted entities.

**Failure mode:** If the input is completely unintelligible, return a HelpRequest asking the user to rephrase specific sections.

### 1.2 Prompt Compiler

**Purpose:** Validate that each structured concern meets minimum completeness requirements.

**Validation checklist (configurable per project):**
- [ ] Specifies what the feature/fix should DO (not just what it should look like)
- [ ] Defines expected inputs and outputs (or states that there are none)
- [ ] Scoped to a single concern (if multiple, suggest splitting)
- [ ] References existing architecture where relevant (for iteration 2+)
- [ ] Includes at least one testable acceptance criterion

**Output on success:** ValidatedPrompt (same as StructuredPrompt, with validation metadata).
**Output on failure:** RejectionReport — specific, actionable error messages per failed check.

### 1.3 Plan Agent

**Purpose:** Generate a development plan from the validated prompt.

**Inputs:**
- ValidatedPrompt
- Project Memory (architecture docs, dependency maps, known issues, previous decisions)

**Output:** DraftPlan containing:
- Architecture decisions with explicit rationale
- Task breakdown with dependencies
- Acceptance criteria per task (must be mechanically testable)
- Scope boundaries (what this iteration explicitly does NOT include)
- Risk assessment (what could go wrong, what's uncertain)

### 1.4 Plan Reviewer

**Purpose:** Adversarial review of the plan before any code is written.

**Review criteria:**
- Does the plan actually address the user's validated prompt?
- Are acceptance criteria specific enough to write tests from?
- Are there missing edge cases?
- Is the scope realistic for a single iteration?
- Do architecture decisions conflict with existing project decisions?

**Loop guard:** Max 2 revision cycles. If the plan still fails review, escalate to human with specific questions about what's ambiguous.

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
