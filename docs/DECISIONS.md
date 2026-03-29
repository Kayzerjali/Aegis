# Aegis — Architectural Decision Log

> Each decision is numbered and immutable once recorded. If a decision is reversed, a new entry references the original.

---

## ADR-001: Three-Stage Pipeline (Plan → Build → Review)

**Date:** 2026-03-29
**Status:** Accepted
**Context:** We need a structure for the development process compiler. Options considered: linear chain, free-form agent swarm, strict staged pipeline.
**Decision:** Three discrete stages with hard gates between them, communicating via typed JSON interface documents.
**Rationale:** Stages map to natural development phases. Hard gates prevent the most common vibe-coding failure: jumping to code before planning. Interface documents enforce decoupling (Interface Segregation Principle).
**Trade-off:** Less flexible than a free-form agent swarm. An agent can't "skip ahead" even if the task is trivial. Accepted because rigidity is the point — flexibility is what causes vibe-coding failures.

---

## ADR-002: Adversarial Agent Separation for Testing

**Date:** 2026-03-29
**Status:** Accepted
**Context:** The central problem — when the same agent writes code and tests, tests inherit the same misunderstanding as the code, producing false positives. This was the primary failure mode in previous vibe-coding attempts.
**Decision:** The Test Agent receives ONLY the PlanDocument (spec). The Implementation Agent receives ONLY the PlanDocument. Neither sees the other's output.
**Rationale:** Tests written from the spec test what the code SHOULD do. Tests written from the code test what the code DOES do. These are fundamentally different things, and conflating them is the root cause of false positives.
**Trade-off:** The test agent may write tests that are hard to satisfy because it doesn't know the implementation approach. This is a feature, not a bug — it forces the implementation to conform to the spec rather than the other way around.

---

## ADR-003: Mutation Testing as Test Quality Gate

**Date:** 2026-03-29
**Status:** Accepted
**Context:** Even with adversarial separation, the test agent could write weak tests (e.g., only testing the happy path). We need a mechanical way to verify test quality.
**Decision:** After test generation, automatically mutate stub code and verify tests catch the mutations. Tests must achieve a configurable mutation score (default 80%) before the implementation agent begins.
**Rationale:** Mutation testing is an established software engineering technique that mechanically proves tests can catch bugs. It does not require LLM judgment.
**Trade-off:** Adds time to the pipeline. Generating and running mutants is computationally cheap but adds latency. Accepted because catching weak tests early prevents the much more expensive debug loop later.

---

## ADR-004: Mechanical Test Execution in Isolated Docker Containers

**Date:** 2026-03-29
**Status:** Accepted
**Context:** Agents have been observed to "interpret" test results optimistically — claiming tests pass when they don't, or misreading error output.
**Decision:** Tests execute in an isolated Docker container. The container returns raw stdout, stderr, and exit code. No LLM touches the test output before the verdict is determined.
**Rationale:** Removes all possibility of LLM-interpreted results. Exit code 0 = pass, non-zero = fail. Binary, mechanical, uncheateable.
**Trade-off:** Requires Docker. Not all environments support Docker easily. Accepted because the alternative (trusting agents to report test results) is the exact failure mode Aegis exists to prevent.

---

## ADR-005: Circuit Breakers with Fresh Agent Escalation

**Date:** 2026-03-29
**Status:** Accepted
**Context:** Debug agents going in circles — the primary pain point from previous attempts. After N failed fix attempts, the agent's context is polluted with its own failed reasoning.
**Decision:** After 3 failed debug attempts, discard the current agent's context entirely. Spin up a fresh agent with clean context: the spec, the tests, the raw failure output, and a structured summary of what was tried.
**Rationale:** Fresh context breaks circular reasoning. The new agent doesn't inherit the previous agent's incorrect assumptions.
**Trade-off:** Discards potentially useful work from the previous agent. Mitigated by providing a structured "what was tried" summary.

---

## ADR-006: LangGraph as Pipeline Orchestrator

**Date:** 2026-03-29
**Status:** Accepted
**Context:** Need a framework for the state machine, conditional routing, checkpointing, and agent coordination. Options: raw Python, LangChain, LangGraph, CrewAI, custom.
**Decision:** LangGraph.
**Rationale:** LangGraph provides directed graph state machines with conditional edges, checkpointing for pause/resume, and durable execution — exactly the primitives needed for a pipeline with loops and circuit breakers. It's production-grade (used by Klarna, Uber, LinkedIn), has 34.5M monthly downloads, and is model-agnostic. It gives us the enforcement mechanism without being opinionated about which agents fill which slots.
**Trade-off:** Steep learning curve compared to CrewAI. Accepted because CrewAI's simplicity becomes limiting for complex workflows, and teams often migrate to LangGraph anyway.

---

## ADR-007: JSON Schema Validated Interface Documents

**Date:** 2026-03-29
**Status:** Accepted
**Context:** Stages need to communicate. Options: function calls, shared state, message passing, typed documents.
**Decision:** All inter-stage communication happens through JSON documents validated against JSON Schema definitions.
**Rationale:** Applies Interface Segregation and Dependency Inversion. Stages depend on schemas, not implementations. Documents are inspectable, testable, and form an automatic audit trail. Schema validation is mechanical — no LLM needed to verify document correctness.
**Trade-off:** More verbose than direct function calls. Adds serialization overhead. Accepted because the decoupling, auditability, and testability benefits far outweigh the verbosity cost.

---

## ADR-008: Python as Implementation Language

**Date:** 2026-03-29
**Status:** Accepted
**Context:** Aegis itself needs to be built in a language the developer knows and that has strong LLM/AI ecosystem support.
**Decision:** Python 3.12+.
**Rationale:** The developer knows Python. LangGraph is Python-native. The AI/ML ecosystem (LLM APIs, testing tools, Docker SDKs) is strongest in Python. Mutation testing tools like `mutmut` are Python-native.
**Trade-off:** Python is slower than Rust/Go for pipeline orchestration. Accepted because Aegis is I/O-bound (waiting on LLM APIs and Docker), not CPU-bound. Python's speed is irrelevant here.

---

## ADR-009: Model Agnosticism with Future LoRA Specialization

**Date:** 2026-03-29
**Status:** Accepted
**Context:** Which LLM should power the agents?
**Decision:** Design all agent interfaces to be model-agnostic (Liskov Substitution). Start with frontier models (Claude for complex reasoning, Gemini for high-volume/cost-sensitive tasks). Collect structured training data from pipeline runs. Fine-tune specialized LoRA adapters after sufficient data (target: 100+ cycles).
**Rationale:** Frontier models are best for initial development. LoRA adapters can specialize agents for their roles (prompt compiler, test writer, debugger) at lower cost and latency. But training requires data that doesn't exist yet.
**Trade-off:** Defers fine-tuning to Phase 5. Accepted because premature optimization of model selection wastes time when the pipeline architecture itself is unvalidated.

---

## ADR-010: Build Pipeline Infrastructure Before Integrating LLMs

**Date:** 2026-03-29
**Status:** Accepted
**Context:** How to approach Phase 0?
**Decision:** Build the complete pipeline skeleton with mock agents first. Mock agents return canned, valid documents. Prove the state machine, schema validation, loop guards, and Docker test runner work before adding LLM intelligence.
**Rationale:** If the pipeline plumbing is broken, LLM agents will mask it with plausible-looking output. Testing infrastructure with deterministic mocks isolates pipeline bugs from agent bugs.
**Trade-off:** Delays the "wow moment" of seeing agents actually work. Accepted because a broken pipeline with real agents is worse than a working pipeline with mock agents.

---

## ADR-011: Collaborative Planning Advisor with Gate-at-Output (replaces ADR-001 Stage 1 detail)

**Date:** 2026-03-29
**Status:** Accepted (supersedes the Preprocessor → Prompt Compiler → Plan Agent → Plan Reviewer design)

**Context:** The original Stage 1 design placed hard gates at the INPUT to planning — a Prompt Compiler that rejected incomplete prompts and sent the user back to try again. This put the entire burden on the user to provide a complete, specific prompt before receiving any AI assistance. In practice, users start with vague ideas and need help refining them, not rejection.

**Decision:** Replace the Preprocessor, Prompt Compiler, Plan Agent, and Plan Reviewer with two components:
1. **Planning Advisor** — A conversational agent that collaboratively develops a plan with the user. It asks questions, proposes architecture, challenges assumptions, and drafts incrementally. It does the heavy lifting of turning vague intent into specific plans.
2. **Readiness Gate** — A mechanical validation checkpoint at the OUTPUT. Before a PlanDocument can enter the Build stage, it must pass a structural checklist (behavioral description, I/O spec, acceptance criteria, scope boundaries, architecture decisions, risk identification). On failure, specific gaps are fed back to the advisor and the conversation continues.

**Rationale:**
- Users don't think in specs. They think in vague intentions. The AI should help them get to specificity.
- Rejection without assistance is demoralizing and causes workflow abandonment.
- The AI is better at structuring requirements than the user is at writing them from scratch.
- Hard gates are preserved (at the output), so the Build stage still receives a complete, validated plan.
- Mirrors how a senior developer mentors a junior developer — collaborative, not gatekeeping.

**Trade-off:** The Planning Advisor is more expensive per invocation than a simple prompt compiler (it's a multi-turn conversation, not a one-shot validation). Accepted because the cost of a good plan is negligible compared to the cost of building from a bad plan. A bad plan causes cascading failures through Build and Review, wasting far more compute than a thorough planning conversation.

**What's preserved from the original design:**
- The hard gate concept (Readiness Gate = the "compiler")
- Mechanical validation (no LLM judges the plan's readiness — structural checks only)
- The PlanDocument schema (unchanged — the output is the same, just produced differently)
- Circuit breaker (max 3 Readiness Gate attempts before human escalation)
