"""Top-level pipeline runner (Stage 6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

from langgraph.graph import END, StateGraph

from aegis.engines.base import EngineAdapter
from aegis.validation.readiness_gate import ReadinessGate
from aegis.validation.schema_validator import SchemaValidator


class PipelineState(TypedDict, total=False):
    # Inputs / dependencies
    prompt: str
    project_root: str
    engine: EngineAdapter
    schema_validator: SchemaValidator
    readiness_gate: ReadinessGate
    readiness_attempts_max: int

    # Counters / bookkeeping
    readiness_attempts_used: int
    errors: list[str]

    # Documents
    plan_document: dict
    readiness_result: dict
    build_report: dict
    review_report: dict

    # Final status
    final_status: str


def run_pipeline(prompt: str, *, project_root: Path, engine: EngineAdapter) -> PipelineState:
    """Full pipeline (Stage 6): plan -> readiness_gate -> build -> review.

    This is the LangGraph-enforced execution path.
    """
    schema_validator = SchemaValidator()
    readiness_gate = ReadinessGate()

    # Initial state.
    state: PipelineState = {
        "prompt": prompt,
        "project_root": str(project_root),
        "engine": engine,
        "schema_validator": schema_validator,
        "readiness_gate": readiness_gate,
        "readiness_attempts_max": 3,
        "readiness_attempts_used": 0,
        "errors": [],
    }

    def plan_node(s: PipelineState) -> PipelineState:
        project = Path(cast(str, s["project_root"]))
        s["current_stage"] = "plan"
        resp = s["engine"].invoke(
            role="planning_advisor",
            prompt=cast(str, s["prompt"]),
            system_prompt="planning_advisor",
            working_directory=project,
        )
        try:
            doc = json.loads(resp.content)
        except Exception as e:
            s["errors"].append(f"Plan stage produced invalid JSON: {e}")
            s["plan_document"] = {}
            return s

        validation = s["schema_validator"].validate(doc)
        if not validation.is_valid:
            s["errors"].append(f"Plan stage schema validation failed: {[e.message for e in validation.errors]}")
        s["plan_document"] = doc
        return s

    def readiness_gate_node(s: PipelineState) -> PipelineState:
        s["current_stage"] = "readiness_gate"
        plan_doc = cast(dict, s.get("plan_document", {}))
        result = s["readiness_gate"].evaluate(plan_doc)
        result_doc = result.to_document()

        # Validate readiness result is itself a valid interface document.
        validation = s["schema_validator"].validate(result_doc)
        if not validation.is_valid:
            s["errors"].append(f"ReadinessResult schema validation failed: {[e.message for e in validation.errors]}")

        s["readiness_result"] = result_doc
        s["readiness_attempts_used"] = cast(int, s.get("readiness_attempts_used", 0)) + 1
        return s

    def route_after_readiness(s: PipelineState) -> str:
        readiness_doc = cast(dict, s["readiness_result"])
        passed = bool(readiness_doc.get("passed", False))
        if passed:
            return "ready"

        used = cast(int, s["readiness_attempts_used"])
        max_attempts = cast(int, s["readiness_attempts_max"])
        if used >= max_attempts:
            return "abort"
        return "not_ready"

    def build_node(s: PipelineState) -> PipelineState:
        s["current_stage"] = "build"
        project = Path(cast(str, s["project_root"]))
        resp = s["engine"].invoke(
            role="build_stage",
            prompt=cast(str, s["prompt"]),
            system_prompt="build_stage",
            working_directory=project,
        )
        doc = json.loads(resp.content)
        validation = s["schema_validator"].validate(doc)
        if not validation.is_valid:
            s["errors"].append(f"BuildReport schema validation failed: {[e.message for e in validation.errors]}")
        s["build_report"] = doc
        return s

    def review_node(s: PipelineState) -> PipelineState:
        s["current_stage"] = "review"
        project = Path(cast(str, s["project_root"]))
        resp = s["engine"].invoke(
            role="review_stage",
            prompt=cast(str, s["prompt"]),
            system_prompt="review_stage",
            working_directory=project,
        )
        doc = json.loads(resp.content)
        validation = s["schema_validator"].validate(doc)
        if not validation.is_valid:
            s["errors"].append(f"ReviewReport schema validation failed: {[e.message for e in validation.errors]}")
        s["review_report"] = doc
        return s

    def abort_node(s: PipelineState) -> PipelineState:
        s["current_stage"] = "abort"
        s["final_status"] = "not_ready"
        return s

    # Build graph: plan -> readiness_gate -> conditional (build | loop | abort) -> review.
    graph = StateGraph(PipelineState)
    graph.add_node("plan", plan_node)
    graph.add_node("readiness_gate", readiness_gate_node)
    graph.add_node("build", build_node)
    graph.add_node("review", review_node)
    graph.add_node("abort", abort_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "readiness_gate")
    graph.add_conditional_edges(
        "readiness_gate",
        route_after_readiness,
        {"ready": "build", "not_ready": "plan", "abort": "abort"},
    )
    graph.add_edge("build", "review")
    graph.add_edge("review", END)
    graph.add_edge("abort", END)

    app = graph.compile()
    final_state = app.invoke(state)
    if "final_status" not in final_state:
        final_state["final_status"] = "success"
    return final_state


def run_plan_stage(
    prompt: str, *, project_root: Path, engine: EngineAdapter, readiness_attempts_max: int = 3
) -> tuple[dict, dict]:
    """Plan stage with readiness gate loop.

    Used by `aegis plan`. This is intentionally not LangGraph-heavy; the full
    LangGraph enforcement lives in `run_pipeline()`.
    """
    schema_validator = SchemaValidator()
    readiness_gate = ReadinessGate()

    last_plan: dict = {}
    last_ready: dict = {}
    for _ in range(readiness_attempts_max):
        resp = engine.invoke(
            role="planning_advisor",
            prompt=prompt,
            system_prompt="planning_advisor",
            working_directory=project_root,
        )
        last_plan = json.loads(resp.content)
        plan_validation = schema_validator.validate(last_plan)
        if not plan_validation.is_valid:
            raise ValueError(f"PlanDocument schema validation failed: {[e.message for e in plan_validation.errors]}")

        result = readiness_gate.evaluate(last_plan)
        last_ready = result.to_document()
        validation = schema_validator.validate(last_ready)
        if validation.is_valid and bool(last_ready.get("passed", False)):
            return last_plan, last_ready

    # If we got here, we never passed readiness.
    return last_plan, last_ready


def run_build_from_plan(*, plan_document: dict, project_root: Path, engine: EngineAdapter) -> dict:
    """Build stage invoked from an already-created PlanDocument (used by `aegis build`)."""
    schema_validator = SchemaValidator()
    readiness_gate = ReadinessGate()

    readiness = readiness_gate.evaluate(plan_document).to_document()
    ready_validation = schema_validator.validate(readiness)
    if not ready_validation.is_valid or not readiness.get("passed", False):
        raise ValueError("PlanDocument did not pass readiness gate")

    resp = engine.invoke(
        role="build_stage",
        prompt="",
        system_prompt="build_stage",
        working_directory=project_root,
    )
    build_report = json.loads(resp.content)
    validation = schema_validator.validate(build_report)
    if not validation.is_valid:
        raise ValueError("BuildReport schema validation failed")
    return build_report

