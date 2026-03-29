"""Configuration loading and project initialization for Aegis.

Handles creating .aegis/ project directories, writing default config,
and loading config with typed access methods.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

from aegis.config.defaults import DEFAULT_CONFIG, _DEFAULT_LOOP_LIMIT_FALLBACK


_CONFIG_FILENAME = "config.toml"
_AEGIS_DIR = ".aegis"
_DOCUMENT_SUBDIRS = ["plans", "builds", "reviews", "sessions"]


@dataclass
class AegisConfig:
    """Typed access to Aegis project configuration."""
    _data: dict = field(default_factory=lambda: copy.deepcopy(DEFAULT_CONFIG))

    def get_engine(self, role: str) -> str:
        engines = self._data.get("engines", {})
        if role in engines:
            return engines[role]
        return engines.get("default", "mock")

    def get_loop_limit(self, key: str) -> int:
        limits = self._data.get("loop_limits", {})
        return limits.get(key, _DEFAULT_LOOP_LIMIT_FALLBACK)

    def get_mutation_threshold(self) -> float:
        thresholds = self._data.get("thresholds", {})
        return thresholds.get("mutation_score", DEFAULT_CONFIG["thresholds"]["mutation_score"])


class ConfigLoader:
    """Loads and initializes Aegis project configuration."""

    @staticmethod
    def initialize(project_path: Path) -> None:
        """Create .aegis/ directory structure with default config. Idempotent."""
        aegis_dir = project_path / _AEGIS_DIR
        aegis_dir.mkdir(exist_ok=True)

        docs_dir = aegis_dir / "documents"
        docs_dir.mkdir(exist_ok=True)
        for subdir in _DOCUMENT_SUBDIRS:
            (docs_dir / subdir).mkdir(exist_ok=True)

        (aegis_dir / "memory").mkdir(exist_ok=True)

        config_path = aegis_dir / _CONFIG_FILENAME
        if not config_path.exists():
            config_path.write_text(_serialize_default_config())

    @staticmethod
    def load(project_path: Path) -> AegisConfig:
        """Load config from .aegis/config.toml, falling back to defaults if missing."""
        config_path = project_path / _AEGIS_DIR / _CONFIG_FILENAME
        if not config_path.exists():
            return AegisConfig()

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception:
            return AegisConfig()

        merged = copy.deepcopy(DEFAULT_CONFIG)
        _deep_merge(merged, data)
        return AegisConfig(_data=merged)


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base, modifying base in place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _serialize_default_config() -> str:
    """Generate the default config.toml content."""
    lines = [
        "# Aegis project configuration",
        "# See docs/IMPLEMENTATION.md for details on each setting",
        "",
        "[engines]",
    ]
    for role, engine in DEFAULT_CONFIG["engines"].items():
        lines.append(f'{role} = "{engine}"')

    lines.append("")
    lines.append("[loop_limits]")
    for key, value in DEFAULT_CONFIG["loop_limits"].items():
        lines.append(f"{key} = {value}")

    lines.append("")
    lines.append("[thresholds]")
    for key, value in DEFAULT_CONFIG["thresholds"].items():
        lines.append(f"{key} = {value}")

    lines.append("")
    return "\n".join(lines)
