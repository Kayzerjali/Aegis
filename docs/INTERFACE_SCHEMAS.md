# Aegis — Interface Document Schemas

> These are draft schemas. They will be formalized as JSON Schema files during implementation.

## Design Rationale

Interface documents are the contracts between pipeline stages. They serve three purposes:

1. **Decoupling** — Stages know nothing about each other. They know about documents.
2. **Validation** — Documents are mechanically validated against schemas before being accepted. No LLM judgment involved.
3. **Auditability** — The chronological stack of documents IS the project history.

All documents include a common header for traceability.

## Common Header

Every interface document includes:

```json
{
  "aegis_version": "0.1.0",
  "document_type": "PlanDocument | BuildReport | ReviewReport | ...",
  "document_id": "uuid-v4",
  "parent_document_id": "uuid-v4 | null",
  "project_id": "string",
  "task_id": "string",
  "timestamp": "ISO-8601",
  "stage": "plan | build | review",
  "status": "draft | validated | rejected | approved"
}
```

The `parent_document_id` creates a linked chain: ReviewReport → BuildReport → PlanDocument. Walk the chain to reconstruct the full history of any feature.

---

## PlanningSession

**Produced by:** Planning Advisor (as a side-effect of the conversation)
**Consumed by:** Project Memory (for audit trail), not consumed by Build stage

The PlanningSession captures the collaborative dialogue for auditability. It is NOT an interface document between stages — the PlanDocument is. The session is archived for context.

```json
{
  "...header": {},
  "raw_user_input": "string (original user text, preserved verbatim)",
  "exchanges": [
    {
      "turn": "int",
      "speaker": "user | advisor",
      "content": "string",
      "readiness_snapshot": {
        "behavioral_description": "met | unmet",
        "input_output_spec": "met | unmet",
        "acceptance_criteria": "met | unmet (N of M required)",
        "scope_boundaries": "met | unmet",
        "architecture_decisions": "met | unmet | not_applicable",
        "risk_identification": "met | unmet"
      }
    }
  ],
  "readiness_gate_attempts": [
    {
      "attempt": "int",
      "gaps": ["string (specific requirements not yet met)"],
      "outcome": "passed | failed"
    }
  ],
  "session_context": {
    "iteration_number": "int (1 for greenfield, 2+ for subsequent)",
    "previous_task_ids": ["string"],
    "project_memory_refs": ["string (documents consulted from Project Memory)"]
  }
}
```

---

## ReadinessResult

**Produced by:** Readiness Gate
**Consumed by:** Planning Advisor (on failure) or pipeline orchestrator (on success)

```json
{
  "...header": {},
  "plan_document_id": "uuid of the DraftPlanDocument being validated",
  "passed": "bool",
  "checklist": [
    {
      "requirement": "behavioral_description | input_output_spec | acceptance_criteria | scope_boundaries | architecture_decisions | risk_identification",
      "status": "met | unmet",
      "detail": "string (what's missing or what satisfied it)"
    }
  ],
  "gaps_summary": "string | null (human-readable summary of what's still needed, null if passed)"
}
```

---

## PlanDocument

**Produced by:** Planning Advisor → Readiness Gate (validated)
**Consumed by:** Test Agent, Implementation Agent, Code Reviewer

This is the central document of the pipeline. Everything downstream derives from it.

```json
{
  "...header": {},
  "user_intent": "string (one-paragraph summary of what the user wants)",
  "architecture": {
    "components": [
      {
        "name": "string",
        "responsibility": "string",
        "interfaces": {
          "inputs": ["string (type and description)"],
          "outputs": ["string (type and description)"]
        },
        "dependencies": ["string (other component names)"]
      }
    ],
    "decisions": [
      {
        "decision": "string (what was decided)",
        "rationale": "string (why)",
        "alternatives_considered": ["string"],
        "trade_offs": "string"
      }
    ]
  },
  "tasks": [
    {
      "task_id": "string",
      "description": "string",
      "acceptance_criteria": [
        {
          "criterion_id": "string",
          "description": "string (must be mechanically testable)",
          "test_approach": "unit | integration | property | e2e"
        }
      ],
      "dependencies": ["string (other task_ids that must complete first)"],
      "estimated_complexity": "low | medium | high",
      "target_files": ["string (file paths to create or modify)"]
    }
  ],
  "scope_boundaries": {
    "in_scope": ["string"],
    "out_of_scope": ["string (explicitly excluded to prevent scope creep)"]
  },
  "risks": [
    {
      "description": "string",
      "likelihood": "low | medium | high",
      "mitigation": "string"
    }
  ],
  "context": {
    "existing_architecture_ref": "string | null (reference to Project Memory)",
    "relevant_previous_tasks": ["string (task_ids)"],
    "known_constraints": ["string"]
  }
}
```

---

## BuildReport

**Produced by:** Build Stage
**Consumed by:** Review Stage

Two variants: success and failure.

### BuildReport (Success)

```json
{
  "...header": {},
  "status": "success",
  "plan_document_id": "uuid (reference to the PlanDocument this implements)",
  "tasks_completed": [
    {
      "task_id": "string",
      "files_created": ["string"],
      "files_modified": ["string"],
      "acceptance_criteria_met": ["criterion_id"]
    }
  ],
  "test_results": {
    "total_tests": "int",
    "passing": "int",
    "failing": 0,
    "mutation_score": "float (0.0-1.0)",
    "mutation_rounds": "int (how many rounds to reach threshold)"
  },
  "build_metrics": {
    "total_iterations": "int",
    "debug_attempts": "int",
    "fresh_agent_invoked": "bool",
    "total_duration_seconds": "int",
    "agents_used": {
      "test_agent": "string (model name)",
      "impl_agent": "string (model name)",
      "debug_agent": "string (model name, if used)"
    }
  },
  "code_diff": "string (unified diff of all changes)"
}
```

### BuildReport (Failure / Escalation)

```json
{
  "...header": {},
  "status": "failed | escalated_to_human",
  "plan_document_id": "uuid",
  "failure_summary": "string (one-paragraph description of what went wrong)",
  "attempts": [
    {
      "attempt_number": "int",
      "agent": "debug_agent | fresh_agent",
      "approach": "string (what the agent tried)",
      "test_output": "string (raw stdout/stderr)",
      "outcome": "still_failing"
    }
  ],
  "agent_hypothesis": "string (the last agent's best guess about root cause)",
  "suggested_human_actions": [
    "string (specific things the human could investigate)"
  ],
  "test_results_at_failure": {
    "total_tests": "int",
    "passing": "int",
    "failing": "int",
    "failing_test_names": ["string"]
  }
}
```

---

## ReviewReport

**Produced by:** Review Stage
**Consumed by:** Project Memory, User

```json
{
  "...header": {},
  "build_report_id": "uuid",
  "verdict": "approved | changes_requested | rejected",
  "checklist": [
    {
      "criterion": "string (from PlanDocument acceptance criteria)",
      "satisfied": "bool",
      "notes": "string | null"
    }
  ],
  "issues": [
    {
      "severity": "critical | major | minor | suggestion",
      "category": "correctness | security | performance | style | documentation",
      "description": "string",
      "location": "string (file:line or component name)",
      "suggested_fix": "string | null"
    }
  ],
  "documentation_updates": {
    "architecture_changes": "bool",
    "new_components": ["string"],
    "modified_interfaces": ["string"],
    "new_dependencies": ["string"]
  },
  "knowledge_entries": [
    {
      "type": "bug_encountered | decision_made | pattern_learned | risk_identified",
      "description": "string",
      "resolution": "string | null",
      "tags": ["string"]
    }
  ]
}
```

---

## Schema Validation Rules

1. **All documents must pass JSON Schema validation before being accepted by the next stage.** This is mechanical — no LLM involved.
2. **Missing required fields = rejection.** The producing agent retries with the schema error as feedback.
3. **`parent_document_id` must reference a valid, existing document.** Orphaned documents are rejected.
4. **Acceptance criteria descriptions must contain at least one verb and one measurable outcome.** (Heuristic check, not perfect, but catches "the app should be good".)
5. **`status` transitions are enforced:** draft → validated → approved. No skipping.
