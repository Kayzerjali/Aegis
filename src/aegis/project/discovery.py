"""Project discovery helpers.

Find the project root by walking upward until `.aegis/config.toml` is found.
"""

from __future__ import annotations

from pathlib import Path


def find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    while True:
        candidate = current / ".aegis" / "config.toml"
        if candidate.exists():
            return current
        if current.parent == current:
            return None
        current = current.parent

