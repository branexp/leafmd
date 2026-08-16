from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRange:
    href: str
    start_id: str | None = None
    end_id: str | None = None
    start_xpath: str | None = None
    end_xpath: str | None = None


@dataclass(frozen=True)
class SemanticEvidence:
    semantic_type: str
    source: str
    confidence: float
    detail: str | None = None


@dataclass
class SectionPlan:
    id: str
    title: str
    type: str
    role: str
    sources: list[SourceRange]
    toc_path: list[str]
    evidence: list[SemanticEvidence]
    confidence: float
    parent_id: str | None = None
    order: int = 0
    output_path: str | None = None


@dataclass(frozen=True)
class OutputTarget:
    path: str
    anchor: str | None = None
