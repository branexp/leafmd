"""Explainable title/filename classification. Not ML."""

from __future__ import annotations

import re

from leafmd.model.publication import Resource
from leafmd.model.section import SemanticEvidence

_RULES: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"\b(title\s*page|titlepage)\b", re.I), "title-page", 0.55),
    (re.compile(r"\b(copyright)\b", re.I), "copyright-page", 0.55),
    (re.compile(r"\b(dedication)\b", re.I), "dedication", 0.5),
    (re.compile(r"\b(foreword)\b", re.I), "foreword", 0.5),
    (re.compile(r"\b(preface)\b", re.I), "preface", 0.5),
    (re.compile(r"\b(acknowledgments?|acknowledgements?)\b", re.I), "acknowledgments", 0.5),
    (re.compile(r"\b(introduction)\b", re.I), "introduction", 0.5),
    (re.compile(r"\b(appendix)\b", re.I), "appendix", 0.5),
    (re.compile(r"\b(glossary)\b", re.I), "glossary", 0.5),
    (re.compile(r"\b(bibliography|works cited)\b", re.I), "bibliography", 0.5),
    (re.compile(r"\b(index)\b", re.I), "index", 0.45),
    (re.compile(r"\b(colophon)\b", re.I), "colophon", 0.5),
    (re.compile(r"\b(chapter|ch\.?)\s*\d+", re.I), "chapter", 0.45),
    (re.compile(r"\bpart\s+\d+", re.I), "part", 0.4),
]


def classify_from_title(title: str, resource: Resource) -> tuple[str, list[SemanticEvidence]]:
    for prop in resource.properties:
        if prop.startswith("rendition:"):
            continue
    haystacks = [title, resource.id, resource.href]
    for pattern, semantic_type, confidence in _RULES:
        for hay in haystacks:
            if pattern.search(hay):
                return semantic_type, [
                    SemanticEvidence(
                        semantic_type=semantic_type,
                        source="heading" if hay == title else "filename",
                        confidence=confidence,
                        detail=hay,
                    )
                ]
    return "chapter", [
        SemanticEvidence(
            semantic_type="chapter",
            source="spine",
            confidence=0.4,
            detail="Default Phase 1 spine document",
        )
    ]
