# Aegis — Development Roadmap

## Phased Approach

Aegis is built in phases. Each phase produces a usable tool AND validates the previous phase.

```
Phase 0: Foundation        ──▶  Core pipeline skeleton, no agents yet
Phase 1: Minimum Viable    ──▶  Single-task pipeline with adversarial testing
Phase 2: Hardened Pipeline ──▶  Loop guards, mutation testing, project memory
Phase 3: Build Thoth       ──▶  Validate Aegis against a real Rust project
Phase 4: Build Eidolon     ──▶  Validate Aegis against a complex systems project
Phase 5: Fine-Tuning       ──▶  Train specialized LoRA adapters from collected data
```

---

## Phase 0: Foundation

**Goal:** Runnable pipeline skeleton with mock agents and real interface documents.

**Deliverables:**
- [ ] Project structure (Python, LangGraph)
- [ ] JSON Schema definitions for all interface documents
- [ ] Schema validation layer (mechanical, no LLM)
- [ ] Pipeline state machine with stage transitions (LangGraph graph)
- [ ] Mock agents that produce valid documents (for testing the pipeline itself)
- [ ] Docker-based test runner container
- [ ] CLI entry point: `aegis run "your prompt here"`

**Key decision:** Build the pipeline infrastructure BEFORE integrating any LLM. The pipeline should work end-to-end with mock agents that return canned documents. This proves the plumbing before adding intelligence.

**Tech stack:**
- Python 3.12+
- LangGraph (state machine, checkpointing, conditional routing)
- JSON Schema (document validation via `jsonschema` library)
- Docker (isolated test execution)
- SQLite (project memory persistence)

**Estimated effort:** 1-2 weeks with AI assistance

---

## Phase 1: Minimum Viable Pipeline

**Goal:** Single-task, end-to-end pipeline with real LLM agents.

**Deliverables:**
- [ ] Prompt Preprocessor agent (LLM-powered)
- [ ] Prompt Compiler agent (LLM + rule-based hybrid)
- [ ] Plan Agent (LLM-powered)
- [ ] Test Agent (LLM-powered, spec-only context)
- [ ] Implementation Agent (LLM-powered, spec-only context)
- [ ] Isolated Test Runner (Docker, mechanical)
- [ ] Basic Debug Agent (LLM-powered, max 3 retries)
- [ ] CLI output showing pipeline progress and stage transitions

**Validation test:** Give Aegis a simple, well-specified task (e.g., "build a Python CLI that converts CSV to JSON with error handling for malformed rows"). Verify:
- Prompt is validated
- Plan is generated with acceptance criteria
- Tests are written from spec alone
- Implementation is written from spec alone
- Tests run in Docker and produce real pass/fail
- Debug agent fixes failures without human intervention

**NOT included yet:** Mutation testing, Fresh Agent escalation, Plan Reviewer, Project Memory, Code Reviewer.

**Estimated effort:** 2-3 weeks with AI assistance

---

## Phase 2: Hardened Pipeline

**Goal:** Full pipeline with all loop guards, mutation testing, and project memory.

**Deliverables:**
- [ ] Plan Reviewer agent (adversarial plan audit)
- [ ] Mutation testing integration (`mutmut` for Python targets)
- [ ] Fresh Agent escalation path
- [ ] All loop guards with configurable iteration limits
- [ ] Human escalation with structured FailureReport
- [ ] Code Reviewer agent
- [ ] Documentation Generator
- [ ] Project Memory (SQLite + structured entries)
- [ ] Multi-task support (pipeline handles task dependencies)
- [ ] Configuration system (thresholds, agent model selection, loop limits)

**Validation test:** Give Aegis a deliberately ambiguous task and verify:
- Prompt Compiler rejects it with specific error messages
- After refinement, pipeline completes successfully
- Mutation testing catches weak tests and forces improvement
- Project Memory correctly records the development cycle
- A second task can reference the first task's context

**Estimated effort:** 3-4 weeks with AI assistance

---

## Phase 3: Build Thoth Using Aegis

**Goal:** Validate Aegis against a real, complex project in an unfamiliar language (Rust).

**Thoth overview:**
- Terminal multiplexer for power users
- Features: terminal multiplexing, filesystem management, git management, hooks
- Similar to Ghostty/WezTerm but with richer workflow features
- Built in Rust (agents handle the language, Aegis ensures quality)

**What this validates:**
- Can Aegis manage a project in a language the user doesn't know?
- Does Project Memory maintain coherence across many development cycles?
- Does mutation testing work with `cargo-mutants` (Rust)?
- Do the escalation paths trigger appropriately for harder problems?
- Does the documentation layer produce useful enough context for fresh agents?

**Estimated effort:** 6-10 weeks with AI assistance (Thoth is a substantial project)

---

## Phase 4: Build Eidolon Using Aegis

**Goal:** Validate Aegis against the hardest project — GUI automation for AI agents.

**Eidolon overview:**
- Tool for AI agents to interact with GUI applications on a virtual monitor
- Removes the human-in-the-loop requirement for visual verification
- Virtual display rendering, screenshot capture, input simulation, visual understanding

**What this validates:**
- Can Aegis handle systems-level complexity?
- Can the pipeline manage projects with hardware/display dependencies?
- Does Eidolon itself become a component of Aegis (visual verification agent)?

**Long-term potential:** Eidolon integrated into Aegis means agents can visually verify GUI applications they build, closing the loop on visual correctness without human review.

**Estimated effort:** 8-12 weeks with AI assistance

---

## Phase 5: Specialization and Fine-Tuning

**Goal:** Train specialized LoRA adapters for each agent role using data collected from Phases 1-4.

**Prerequisites:**
- Sufficient pipeline run data (target: 100+ complete cycles)
- Identified patterns in agent performance per role
- Open-source base model selection (Llama, Mistral, DeepSeek, or current best)

**Training targets:**
| Agent Role | Training Signal | Expected Improvement |
|-----------|----------------|---------------------|
| Prompt Compiler | Rejected vs. accepted prompts | Faster, cheaper validation |
| Plan Agent | Plans that led to successful builds vs. failed builds | Better first-attempt plans |
| Test Agent | Test suites with high mutation scores | Stronger tests from spec |
| Debug Agent | Successful fix attempts with minimal iterations | More efficient debugging |

**Infrastructure:** User's VPS or cloud GPU rental for training runs. LoRA is lightweight — a single consumer GPU (16GB+ VRAM) is sufficient.

---

## Infrastructure Plan

### Development Environment (Phases 0-2)
- Local development or Cursor Cloud Agents
- Docker for test isolation
- GitHub for version control

### Production Environment (Phases 3+)
- User's VPS running Aegis pipeline
- Docker containers per agent execution
- Optional: AgentsMesh for multi-agent fleet management if needed
- Cursor for interactive work, Aegis CLI for autonomous pipeline runs

### API Keys Required
- At least one frontier model API (Claude, GPT, or Gemini)
- Recommended: Gemini for high-volume tasks (cost-effective), Claude for complex reasoning tasks
