# Aegis

> A Development Process Compiler for AI-Assisted Software Engineering

Aegis is a meta-framework that enforces structured, verifiable development practices on AI coding agents. It does not write code — it governs agents that write code, the same way a compiler governs how developers write code.

## Status: Planning

This project is in the architectural planning phase. See the [`docs/`](docs/) directory for:

- **[VISION.md](docs/VISION.md)** — Problem statement, thesis, and goals
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Three-stage pipeline, SOLID principles mapping, agent separation
- **[PIPELINE.md](docs/PIPELINE.md)** — Detailed breakdown of every pipeline component and data flow
- **[INTERFACE_SCHEMAS.md](docs/INTERFACE_SCHEMAS.md)** — Draft JSON schemas for all interface documents
- **[ROADMAP.md](docs/ROADMAP.md)** — Phased development plan (Aegis → Thoth → Eidolon)
- **[DECISIONS.md](docs/DECISIONS.md)** — Architectural Decision Records (ADRs)

## Core Ideas

1. **Prompt Compiler** — Rejects vague or incomplete prompts with specific error messages, like a compiler rejects syntax errors.
2. **Adversarial Agent Separation** — The agent writing tests never sees the implementation. The agent writing code never sees the tests. Both work from the spec alone.
3. **Mutation Testing** — Automatically verifies that AI-generated tests can actually catch bugs, eliminating false positives.
4. **Hard State Gates** — Pipeline blocks until requirements are met. No skipping steps, no suggestions — enforcement.
5. **Circuit Breakers** — After repeated failures, discard polluted context and escalate to a fresh agent or human.

## Related Projects

- **Thoth** — Terminal multiplexer (to be built using Aegis)
- **Eidolon** — GUI automation tool for AI agents (to be built using Aegis)
