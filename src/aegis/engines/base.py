"""Engine adapter interface (Stage 5).

This defines the boundary between Aegis pipeline stages and AI backends.
Sprint 1 uses a mock engine; later stages add real adapters without
changing pipeline logic (Liskov Substitution).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EngineResponse:
    """A normalized engine response."""

    content: str
    usage: dict = field(default_factory=dict)
    model: str = "unknown"
    raw: dict = field(default_factory=dict)


class EngineAdapter(ABC):
    """Abstract engine interface."""

    @abstractmethod
    def invoke(
        self,
        *,
        role: str,
        prompt: str,
        system_prompt: str,
        working_directory: Path,
    ) -> EngineResponse:
        """Single-turn invocation: prompt/system_prompt in, content out."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the engine is ready to be used."""

