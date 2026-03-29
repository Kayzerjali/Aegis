# Aegis — Vision

> A Development Process Compiler for AI-Assisted Software Engineering

## The Problem

AI-assisted development ("vibe coding") fails at an estimated 70%+ rate beyond the demo stage. The failures are not random — they follow predictable patterns:

1. **No architecture before prompting.** Developers jump into code generation without defining structure, leading to architectural collapse as features accumulate.
2. **Vague, unstructured prompts.** Agents receive ambiguous instructions and fill gaps with hallucinated assumptions.
3. **False positive verification loops.** When the same agent writes code AND tests, the tests inherit the same flawed understanding as the code. The agent "fixes" a bug, writes a test that confirms its own misunderstanding, and reports success. The bug remains.
4. **Context pollution and circular reasoning.** After 20-30 messages, agents lose coherence. When asked to fix failures, they attempt the same broken approach repeatedly, reporting success each time.
5. **No ground truth.** There is no mechanical verification layer — agents self-assess through the same reasoning that produced the bug.

These are not tooling problems. They are **structural** problems. Better prompts, larger context windows, and smarter models mitigate them but do not eliminate them. The solution must be architectural.

## The Thesis

**A strict, compiler-like meta-framework can enforce disciplined development practices on AI coding agents the same way a compiler enforces language rules on human developers.**

A compiler does not suggest you fix your syntax. It rejects your code until you do. Aegis applies this principle to the entire development process:

- Vague prompts are **rejected**, not interpreted.
- Plans are **validated** before any code is generated.
- Tests are written by an agent that **never sees the implementation**.
- Test quality is verified by **mutation testing**, not by LLM self-assessment.
- Test execution happens in **isolated environments** with mechanical pass/fail — no LLM interprets the results.
- Failed fix attempts are **circuit-broken** and escalated to a fresh agent with clean context.
- Every stage produces **structured interface documents** that decouple the pipeline and provide a complete audit trail.

## Goals

### Primary
- Eliminate the false-positive verification loop through adversarial agent separation and mutation testing.
- Enforce a plan-first, test-first development process as hard gates (not suggestions).
- Enable non-expert developers to produce professional-grade, tested, documented software through AI agents they can trust.

### Secondary
- Provide a living documentation system that allows any agent to "step in" to an unfamiliar codebase with full context.
- Be model-agnostic — any LLM (Claude, GPT, Gemini, local/fine-tuned) can fill any agent role, as long as it conforms to the interface.
- Collect structured data from pipeline runs to enable future fine-tuning of specialized agent models (LoRA adapters).

### Stretch
- Serve as the development framework for building Thoth (terminal multiplexer) and Eidolon (GUI automation for agents), validating Aegis against real, complex projects.
- Contribute novel techniques (mutation-tested AI code, adversarial agent separation) to the broader AI-assisted development ecosystem.

## What Aegis Is Not

- **Not a coding agent.** Aegis does not write code. It governs agents that write code.
- **Not a prompt template library.** Aegis does not help you write better prompts. It rejects bad ones.
- **Not a wrapper around one model.** Aegis is model-agnostic by design (Dependency Inversion Principle).
- **Not a suggestion system.** Its gates are hard — the pipeline blocks until requirements are met.

## Name

Aegis (Greek: Αἰγίς) — the divine shield of Zeus. A protective barrier that nothing passes through unchecked.

Thematic companion to:
- **Thoth** — Egyptian god of knowledge and writing (terminal multiplexer project)
- **Eidolon** — Greek "phantom/image" (GUI automation for agents project)
