"""Readiness Gate for PlanDocument validation.

Checks whether a PlanDocument is complete enough for the Build stage.
Distinct from schema validation: schema checks structure, the gate checks
semantic completeness (enough acceptance criteria, non-trivial descriptions,
scope boundaries defined, risks identified).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

_MIN_INTENT_LENGTH = 20


@dataclass
class ReadinessResult:
    """Outcome of evaluating a PlanDocument against the readiness checklist."""
    passed: bool
    checklist: list[dict] = field(default_factory=list)
    gaps_summary: str | None = None
    plan_document_id: str = ""

    def to_document(self) -> dict:
        """Serialize to a ReadinessResult interface document that passes schema validation."""
        return {
            "aegis_version": "0.1.0",
            "document_type": "ReadinessResult",
            "document_id": str(uuid.uuid4()),
            "parent_document_id": self.plan_document_id or None,
            "project_id": "unknown",
            "task_id": "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": "plan",
            "status": "validated" if self.passed else "rejected",
            "plan_document_id": self.plan_document_id,
            "passed": self.passed,
            "checklist": self.checklist,
            "gaps_summary": self.gaps_summary,
        }


class ReadinessGate:
    """Evaluates whether a PlanDocument meets the minimum requirements for the Build stage."""

    def __init__(self, min_acceptance_criteria: int = 3):
        self._min_acceptance_criteria = min_acceptance_criteria

    def evaluate(self, plan: dict) -> ReadinessResult:
        plan_id = plan.get("document_id", "")
        checklist = [
            self._check_behavioral_description(plan),
            self._check_input_output_spec(plan),
            self._check_acceptance_criteria(plan),
            self._check_scope_boundaries(plan),
            self._check_architecture_decisions(plan),
            self._check_risk_identification(plan),
        ]

        unmet = [c for c in checklist if c["status"] == "unmet"]
        passed = len(unmet) == 0

        gaps_summary = None
        if not passed:
            gap_details = [c["detail"] for c in unmet]
            gaps_summary = "; ".join(gap_details)

        return ReadinessResult(
            passed=passed,
            checklist=checklist,
            gaps_summary=gaps_summary,
            plan_document_id=plan_id,
        )

    def _check_behavioral_description(self, plan: dict) -> dict:
        intent = plan.get("user_intent", "")
        if isinstance(intent, str) and len(intent.strip()) >= _MIN_INTENT_LENGTH:
            return {"requirement": "behavioral_description", "status": "met", "detail": "User intent is present and sufficiently detailed"}
        return {"requirement": "behavioral_description", "status": "unmet", "detail": f"User intent is missing or too brief (minimum {_MIN_INTENT_LENGTH} characters)"}

    def _check_input_output_spec(self, plan: dict) -> dict:
        tasks = plan.get("tasks", [])
        if not tasks:
            return {"requirement": "input_output_spec", "status": "unmet", "detail": "No tasks defined"}
        for task in tasks:
            desc = task.get("description", "")
            if not isinstance(desc, str) or len(desc.strip()) == 0:
                return {"requirement": "input_output_spec", "status": "unmet", "detail": "One or more tasks have empty descriptions"}
        return {"requirement": "input_output_spec", "status": "met", "detail": "All tasks have descriptions"}

    def _check_acceptance_criteria(self, plan: dict) -> dict:
        tasks = plan.get("tasks", [])
        if not tasks:
            return {"requirement": "acceptance_criteria", "status": "unmet", "detail": "No tasks defined, so no acceptance criteria"}
        total_criteria = sum(len(t.get("acceptance_criteria", [])) for t in tasks)
        if total_criteria < self._min_acceptance_criteria:
            return {
                "requirement": "acceptance_criteria",
                "status": "unmet",
                "detail": f"Found {total_criteria} acceptance criteria, minimum is {self._min_acceptance_criteria}",
            }
        return {"requirement": "acceptance_criteria", "status": "met", "detail": f"{total_criteria} acceptance criteria defined"}

    def _check_scope_boundaries(self, plan: dict) -> dict:
        boundaries = plan.get("scope_boundaries", {})
        in_scope = boundaries.get("in_scope", [])
        out_of_scope = boundaries.get("out_of_scope", [])
        if not in_scope:
            return {"requirement": "scope_boundaries", "status": "unmet", "detail": "in_scope is empty or missing"}
        if not out_of_scope:
            return {"requirement": "scope_boundaries", "status": "unmet", "detail": "out_of_scope is empty or missing — explicitly state what is NOT included"}
        return {"requirement": "scope_boundaries", "status": "met", "detail": "Both in_scope and out_of_scope defined"}

    def _check_architecture_decisions(self, plan: dict) -> dict:
        arch = plan.get("architecture", {})
        if not arch:
            return {"requirement": "architecture_decisions", "status": "unmet", "detail": "No architecture section defined"}
        components = arch.get("components", [])
        decisions = arch.get("decisions", [])
        if not components and not decisions:
            return {"requirement": "architecture_decisions", "status": "unmet", "detail": "Architecture section has no components or decisions"}
        return {"requirement": "architecture_decisions", "status": "met", "detail": f"{len(components)} components, {len(decisions)} decisions defined"}

    def _check_risk_identification(self, plan: dict) -> dict:
        risks = plan.get("risks", [])
        if not risks:
            return {"requirement": "risk_identification", "status": "unmet", "detail": "No risks identified — consider what could go wrong"}
        return {"requirement": "risk_identification", "status": "met", "detail": f"{len(risks)} risk(s) identified"}
