"""Mock engine adapter (Stage 5).

Deterministic engine for Sprint 1 that returns pre-configured responses.
Used to validate the pipeline plumbing without any real LLM calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aegis.engines.base import EngineAdapter, EngineResponse


@dataclass
class MockEngineConfig:
    # Role -> list of documents/responses. If more calls are made than entries,
    # the last entry is repeated.
    role_to_documents: dict[str, list[Any]]
    model_name: str = "mock"


class MockEngine(EngineAdapter):
    def __init__(self, config: MockEngineConfig):
        self._config = config
        self._call_counts: dict[str, int] = {}

    def is_available(self) -> bool:
        return True

    def invoke(
        self,
        *,
        role: str,
        prompt: str,
        system_prompt: str,
        working_directory: Path,
    ) -> EngineResponse:
        if role not in self._config.role_to_documents:
            raise ValueError(f"MockEngine has no configured responses for role={role!r}")

        idx = self._call_counts.get(role, 0)
        self._call_counts[role] = idx + 1

        docs = self._config.role_to_documents[role]
        doc_or_str = docs[min(idx, len(docs) - 1)]

        if isinstance(doc_or_str, str):
            content = doc_or_str
            raw: dict[str, Any] = {"provided_content": "string"}
        else:
            content = json.dumps(doc_or_str)
            raw = {"provided_content": "json_object"}

        return EngineResponse(
            content=content,
            usage={"input_tokens": 0, "output_tokens": 0},
            model=self._config.model_name,
            raw={"role": role, **raw},
        )

