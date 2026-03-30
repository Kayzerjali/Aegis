import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from aegis.cli.main import cli
from aegis.engines.mock import MockEngine, MockEngineConfig
from aegis.pipeline.default_docs import (
    sample_build_report,
    sample_plan_document,
    sample_review_report,
)
from aegis.pipeline.runner import run_build_from_plan, run_pipeline, run_plan_stage
from aegis.storage.doc_store import load_latest_document
from aegis.validation.readiness_gate import ReadinessGate
from aegis.validation.schema_validator import SchemaValidator


@pytest.fixture
def schema_validator():
    return SchemaValidator()


@pytest.fixture
def readiness_gate():
    return ReadinessGate()


def test_mock_engine_returns_json_content():
    engine = MockEngine(
        MockEngineConfig(
            role_to_documents={
                "planning_advisor": [sample_plan_document()],
            }
        )
    )
    resp = engine.invoke(
        role="planning_advisor",
        prompt="x",
        system_prompt="planning_advisor",
        working_directory=Path("."),
    )
    doc = json.loads(resp.content)
    assert doc["document_type"] == "PlanDocument"
    assert resp.model == "mock"


def test_pipeline_end_to_end_with_valid_mock(tmp_path):
    engine = MockEngine(
        MockEngineConfig(
            role_to_documents={
                "planning_advisor": [sample_plan_document()],
                "build_stage": [sample_build_report()],
                "review_stage": [sample_review_report()],
            }
        )
    )

    state = run_pipeline("whatever", project_root=tmp_path, engine=engine)
    assert state["final_status"] == "success"
    assert "plan_document" in state
    assert "build_report" in state
    assert "review_report" in state

    sv = SchemaValidator()
    assert sv.validate(state["plan_document"]).is_valid
    assert sv.validate(state["build_report"]).is_valid
    assert sv.validate(state["review_report"]).is_valid
    assert state["readiness_result"]["passed"] is True


def test_pipeline_stops_before_build_when_readiness_fails(tmp_path):
    invalid_plan = sample_plan_document()
    invalid_plan["risks"] = []  # readiness gate requires at least one risk

    engine = MockEngine(
        MockEngineConfig(
            role_to_documents={
                "planning_advisor": [invalid_plan],
                "build_stage": [sample_build_report()],
                "review_stage": [sample_review_report()],
            }
        )
    )

    # With invalid plan, ReadinessGate should reject and graph aborts.
    state = run_pipeline("whatever", project_root=tmp_path, engine=engine)
    assert state["final_status"] == "not_ready"
    assert "build_report" not in state
    assert state["readiness_result"]["passed"] is False


def test_build_from_plan_rejects_unready_plan(tmp_path):
    engine = MockEngine(
        MockEngineConfig(
            role_to_documents={
                "build_stage": [sample_build_report()],
            }
        )
    )

    plan = sample_plan_document()
    plan["risks"] = []
    with pytest.raises(ValueError):
        run_build_from_plan(plan_document=plan, project_root=tmp_path, engine=engine)


def test_cli_init_plan_build_status(tmp_path, monkeypatch):
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    # init
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0

    # plan (run from a subdirectory to ensure discovery works)
    subdir = tmp_path / "work"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    result = runner.invoke(cli, ["plan", "--prompt", "Build a CSV->JSON CLI"])
    assert result.exit_code == 0, result.output

    project_root = tmp_path
    plan_doc = load_latest_document(project_root, "plans")
    assert SchemaValidator().validate(plan_doc).is_valid
    assert plan_doc["document_type"] == "PlanDocument"

    # build
    result = runner.invoke(cli, ["build"])
    assert result.exit_code == 0, result.output

    build_doc = load_latest_document(project_root, "builds")
    assert SchemaValidator().validate(build_doc).is_valid
    assert build_doc["document_type"] == "BuildReport"

    # status
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "Plans" in result.output


def test_cli_build_without_plan_errors(tmp_path, monkeypatch):
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0

    result = runner.invoke(cli, ["build"])
    assert result.exit_code != 0
    assert "No PlanDocument found" in result.output


def test_cli_outside_project_errors(tmp_path, monkeypatch):
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli, ["build"])
    assert result.exit_code != 0
    assert "Run `aegis init`" in result.output

