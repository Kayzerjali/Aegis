"""Document persistence and retrieval for Aegis (Stage 7 support)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


_DOC_SUBDIRS = {
    "plans": "plans",
    "builds": "builds",
    "reviews": "reviews",
    "sessions": "sessions",
}


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def documents_dir(project_root: Path) -> Path:
    return _ensure_dir(project_root / ".aegis" / "documents")


def doc_subdir(project_root: Path, subdir: str) -> Path:
    return _ensure_dir(documents_dir(project_root) / _DOC_SUBDIRS[subdir])


def save_document(project_root: Path, document: dict, subdir: str) -> Path:
    """Save a JSON document and return the file path."""
    out_dir = doc_subdir(project_root, subdir)

    # Use document_id when present for stable naming.
    doc_id = document.get("document_id", None)
    stage = document.get("stage", "unknown")
    filename = f"{document.get('document_type','document')}_{stage}_{doc_id or 'no-id'}.json"
    path = out_dir / filename

    # Avoid accidental overwrite: if the file exists, add a numeric suffix.
    if path.exists():
        i = 1
        while True:
            alt = out_dir / f"{filename[:-5]}_{i}.json"
            if not alt.exists():
                path = alt
                break
            i += 1

    path.write_text(json.dumps(document, indent=2, sort_keys=True))
    return path


def _iter_json_files(path: Path) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def load_latest_document(project_root: Path, subdir: str) -> dict:
    latest_dir = project_root / ".aegis" / "documents" / _DOC_SUBDIRS[subdir]
    files = list(_iter_json_files(latest_dir))
    if not files:
        raise FileNotFoundError(f"No documents found in {latest_dir}")

    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def list_recent_documents(project_root: Path, subdir: str, limit: int = 10) -> list[dict]:
    recent = []
    latest_dir = project_root / ".aegis" / "documents" / _DOC_SUBDIRS[subdir]
    for p in list(_iter_json_files(latest_dir))[:limit]:
        with open(p, "r", encoding="utf-8") as f:
            recent.append(json.load(f))
    return recent

