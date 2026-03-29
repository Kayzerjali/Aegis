"""Tests for the configuration system.

Verifies that:
- aegis init creates .aegis/ directory with config and subdirectories
- Running init twice does not overwrite existing config
- Config loader returns correct default values
- Config values are accessible by key
- Missing config file is handled gracefully
"""

import os
import pytest
from pathlib import Path

from aegis.config.loader import ConfigLoader
from aegis.config.defaults import DEFAULT_CONFIG


@pytest.fixture
def project_dir(tmp_path):
    """A temporary directory acting as a project root."""
    return tmp_path


@pytest.fixture
def initialized_dir(project_dir):
    """A project directory with .aegis/ already initialized."""
    ConfigLoader.initialize(project_dir)
    return project_dir


class TestInitialization:
    def test_init_creates_aegis_directory(self, project_dir):
        ConfigLoader.initialize(project_dir)
        assert (project_dir / ".aegis").is_dir()

    def test_init_creates_config_file(self, project_dir):
        ConfigLoader.initialize(project_dir)
        assert (project_dir / ".aegis" / "config.toml").is_file()

    def test_init_creates_documents_subdirectories(self, project_dir):
        ConfigLoader.initialize(project_dir)
        docs = project_dir / ".aegis" / "documents"
        assert docs.is_dir()
        assert (docs / "plans").is_dir()
        assert (docs / "builds").is_dir()
        assert (docs / "reviews").is_dir()
        assert (docs / "sessions").is_dir()

    def test_init_creates_memory_directory(self, project_dir):
        ConfigLoader.initialize(project_dir)
        assert (project_dir / ".aegis" / "memory").is_dir()

    def test_init_config_is_valid_toml(self, project_dir):
        ConfigLoader.initialize(project_dir)
        config = ConfigLoader.load(project_dir)
        assert config is not None


class TestIdempotency:
    def test_init_twice_preserves_existing_config(self, project_dir):
        ConfigLoader.initialize(project_dir)
        config_path = project_dir / ".aegis" / "config.toml"
        config_path.write_text(config_path.read_text() + "\n# user comment\n")
        original_content = config_path.read_text()

        ConfigLoader.initialize(project_dir)
        assert config_path.read_text() == original_content

    def test_init_twice_does_not_error(self, project_dir):
        ConfigLoader.initialize(project_dir)
        ConfigLoader.initialize(project_dir)


class TestConfigLoading:
    def test_load_returns_default_engine_assignments(self, initialized_dir):
        config = ConfigLoader.load(initialized_dir)
        assert config.get_engine("planning_advisor") is not None
        assert config.get_engine("test_agent") is not None
        assert config.get_engine("impl_agent") is not None

    def test_load_returns_default_loop_limits(self, initialized_dir):
        config = ConfigLoader.load(initialized_dir)
        assert config.get_loop_limit("debug_retries") > 0
        assert config.get_loop_limit("mutation_rounds") > 0
        assert config.get_loop_limit("readiness_attempts") > 0

    def test_load_returns_mutation_threshold(self, initialized_dir):
        config = ConfigLoader.load(initialized_dir)
        threshold = config.get_mutation_threshold()
        assert 0.0 <= threshold <= 1.0

    def test_defaults_match_expected_values(self, initialized_dir):
        config = ConfigLoader.load(initialized_dir)
        assert config.get_loop_limit("debug_retries") == DEFAULT_CONFIG["loop_limits"]["debug_retries"]
        assert config.get_mutation_threshold() == DEFAULT_CONFIG["thresholds"]["mutation_score"]


class TestMissingConfig:
    def test_load_without_init_uses_defaults(self, project_dir):
        config = ConfigLoader.load(project_dir)
        assert config.get_engine("test_agent") is not None

    def test_load_without_init_does_not_crash(self, project_dir):
        config = ConfigLoader.load(project_dir)
        assert config is not None


class TestConfigAccess:
    def test_get_engine_for_unknown_role_returns_default(self, initialized_dir):
        config = ConfigLoader.load(initialized_dir)
        engine = config.get_engine("nonexistent_role")
        assert engine == config.get_engine("default")

    def test_get_loop_limit_for_unknown_key_returns_sensible_default(self, initialized_dir):
        config = ConfigLoader.load(initialized_dir)
        limit = config.get_loop_limit("nonexistent_limit")
        assert isinstance(limit, int)
        assert limit > 0
