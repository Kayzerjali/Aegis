from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console

from aegis.config.loader import ConfigLoader
from aegis.engines.base import EngineAdapter
from aegis.engines.mock import MockEngine, MockEngineConfig
from aegis.pipeline.default_docs import sample_build_report, sample_plan_document, sample_review_report
from aegis.pipeline.runner import run_build_from_plan, run_plan_stage
from aegis.project.discovery import find_project_root
from aegis.storage.doc_store import load_latest_document, save_document
from aegis.validation.readiness_gate import ReadinessGate
from aegis.validation.schema_validator import SchemaValidator


console = Console()


def _require_project() -> Path:
    root = find_project_root(Path.cwd())
    if root is None:
        raise click.ClickException(
            "Not in an initialized Aegis project. Run `aegis init` in the project root."
        )
    return root


def _default_mock_engine_for_plan() -> EngineAdapter:
    return MockEngine(
        MockEngineConfig(
            role_to_documents={
                "planning_advisor": [sample_plan_document()],
                # Unused by `aegis plan` command, but kept for completeness.
                "build_stage": [sample_build_report()],
                "review_stage": [sample_review_report()],
            }
        )
    )


def _default_mock_engine_for_build() -> EngineAdapter:
    return MockEngine(
        MockEngineConfig(
            role_to_documents={
                "build_stage": [sample_build_report()],
                "planning_advisor": [sample_plan_document()],  # not used by build_from_plan
                "review_stage": [sample_review_report()],
            }
        )
    )


@click.group()
@click.version_option(package_name="aegis-dev")
def cli():
    """Aegis — Development Process Compiler."""


@cli.command()
def init():
    """Initialize an Aegis project in the current directory."""
    ConfigLoader.initialize(Path.cwd())
    console.print("[green]Initialized Aegis project[/green] in current directory.")


@cli.command()
@click.option("--prompt", default="Build a CLI tool that converts CSV to JSON.", show_default=True)
def plan(prompt: str):
    """Run the planning stage and save a PlanDocument."""
    project_root = _require_project()
    config = ConfigLoader.load(project_root)
    readiness_attempts = config.get_loop_limit("readiness_attempts")

    engine = _default_mock_engine_for_plan()
    plan_document, _readiness_result = run_plan_stage(
        prompt, project_root=project_root, engine=engine, readiness_attempts_max=readiness_attempts
    )

    saved = save_document(project_root, plan_document, "plans")
    console.print(f"[green]Saved PlanDocument[/green] -> {saved}")


@cli.command()
def build():
    """Run the build stage on the latest PlanDocument."""
    project_root = _require_project()
    schema_validator = SchemaValidator()
    readiness_gate = ReadinessGate()

    try:
        plan_document = load_latest_document(project_root, "plans")
    except FileNotFoundError:
        raise click.ClickException("No PlanDocument found. Run `aegis plan` first.")

    # Validate + readiness gate before invoking the build engine.
    plan_validation = schema_validator.validate(plan_document)
    if not plan_validation.is_valid:
        raise click.ClickException(
            "Latest PlanDocument is invalid: " + "; ".join([e.message for e in plan_validation.errors])
        )

    readiness_result = readiness_gate.evaluate(plan_document).to_document()
    if not readiness_result.get("passed", False):
        gaps = readiness_result.get("gaps_summary") or "Plan is not ready to build."
        raise click.ClickException("Readiness Gate rejected the plan: " + gaps)

    engine = _default_mock_engine_for_build()
    build_report = run_build_from_plan(
        plan_document=plan_document, project_root=project_root, engine=engine
    )
    saved = save_document(project_root, build_report, "builds")
    console.print(f"[green]Saved BuildReport[/green] -> {saved}")


@cli.command()
def status():
    """Show recent documents and their statuses."""
    project_root = _require_project()

    def summarize(subdir: str):
        try:
            docs = _load_recent(subdir)
        except FileNotFoundError:
            return []
        out = []
        for d in docs:
            out.append(
                {
                    "type": d.get("document_type"),
                    "timestamp": d.get("timestamp"),
                    "status": d.get("status"),
                }
            )
        return out

    plans = summarize("plans")
    builds = summarize("builds")
    reviews = summarize("reviews")

    console.print("[bold]Plans[/bold]")
    for item in plans[:5]:
        console.print(f"- {item['type']} @ {item['timestamp']} status={item['status']}")
    console.print("[bold]Builds[/bold]")
    for item in builds[:5]:
        console.print(f"- {item['type']} @ {item['timestamp']} status={item['status']}")
    console.print("[bold]Reviews[/bold]")
    for item in reviews[:5]:
        console.print(f"- {item['type']} @ {item['timestamp']} status={item['status']}")


def _load_recent(subdir: str) -> list[dict]:
    project_root = _require_project()
    from aegis.storage.doc_store import list_recent_documents

    return list_recent_documents(project_root, subdir=subdir, limit=10)
