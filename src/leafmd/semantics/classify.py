"""Explainable, evidence-ranked semantic classification. No ML."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from leafmd.model.publication import Resource
from leafmd.model.section import SemanticEvidence

# Deliberately ordered from specific to broad within a single evidence source.
_RULES: tuple[tuple[re.Pattern[str], str, float], ...] = (
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
    (re.compile(r"\bindex\b", re.I), "index", 0.45),
    (re.compile(r"\b(colophon)\b", re.I), "colophon", 0.5),
    (re.compile(r"\babout\s+the\s+author\b", re.I), "about-author", 0.55),
    (re.compile(r"\b(books\s+by|also\s+available)\b", re.I), "other", 0.45),
    (re.compile(r"\b(chapter|ch\.?)\s*\d+\b", re.I), "chapter", 0.45),
    (re.compile(r"\bpart\s+\d+\b", re.I), "part", 0.4),
)

_PROPERTY_TYPES = {
    "titlepage": "title-page",
    "title-page": "title-page",
    "copyright-page": "copyright-page",
    "dedication": "dedication",
    "foreword": "foreword",
    "preface": "preface",
    "acknowledgments": "acknowledgments",
    "acknowledgements": "acknowledgments",
    "introduction": "introduction",
    "appendix": "appendix",
    "glossary": "glossary",
    "bibliography": "bibliography",
    "index": "index",
    "colophon": "colophon",
    "chapter": "chapter",
    "part": "part",
    "cover": "cover",
    "cover-image": "cover",
    "about-author": "about-author",
    "other": "other",
}


def _match(value: str | None) -> tuple[str, float] | None:
    if not value:
        return None
    for pattern, semantic_type, confidence in _RULES:
        if pattern.search(value):
            return semantic_type, confidence
    return None


def _evidence(semantic_type: str, source: str, confidence: float, detail: str) -> list[SemanticEvidence]:
    return [SemanticEvidence(semantic_type, source, confidence, detail)]


def classify_section(
    title: str,
    resource: Resource,
    *,
    landmark: str | None = None,
    nav_label: str | None = None,
    guide_type: str | None = None,
    ncx_title: str | None = None,
    headings: Sequence[str] = (),
    book_title: str | None = None,
    sibling_types: Iterable[str] = (),
) -> tuple[str, list[SemanticEvidence]]:
    """Classify a spine resource, choosing the highest-ranked explanation.

    ``title`` remains the legacy heading input.  Callers with parsed navigation
    should pass each independent source explicitly; their precedence is OPF
    properties, landmark, nav, guide, NCX, headings, then filename/id.
    """
    # OPF epub:type/properties are the strongest available document evidence.
    for prop in resource.properties:
        token = prop.lower().split("#")[-1].split(":")[-1]
        semantic_type = _PROPERTY_TYPES.get(token)
        if semantic_type:
            return semantic_type, _evidence(semantic_type, "epub:type", 0.95, prop)

    for source, value, confidence in (
        ("landmark", landmark, 0.9),
        ("nav", nav_label, 0.8),
        ("guide", guide_type, 0.75),
        ("ncx", ncx_title, 0.7),
    ):
        match = _match(value)
        if match:
            semantic_type, rule_confidence = match
            return semantic_type, _evidence(semantic_type, source, confidence + rule_confidence / 100, value or "")

    # A caller may provide headings separately; title is retained as the first
    # heading for backwards compatibility with classify_from_title.
    heading_values = list(headings)
    if title and title not in heading_values:
        heading_values.insert(0, title)
    for heading in heading_values:
        match = _match(heading)
        if match:
            semantic_type, confidence = match
            return semantic_type, _evidence(semantic_type, "heading", confidence, heading)

    filename = f"{resource.id} {resource.href}"
    lowered = filename.lower()
    # These aliases occur in common EPUB front/back matter naming schemes.
    boundary = r"(?:^|[._\-\s])"
    if re.search(boundary + r"cover(?:[._\-\s]|$)", lowered) or title.strip() == ".":
        return "cover", _evidence("cover", "filename", 0.65, filename)
    if re.search(r"about[-_ ]?the[-_ ]?author|" + boundary + r"ata(?:[._\-\s]|$)", lowered):
        return "about-author", _evidence("about-author", "filename", 0.65, filename)
    if re.search(r"books[-_ ]?by|also[-_ ]?available|" + boundary + r"bm\d+(?:[._\-\s]|$)", lowered):
        return "other", _evidence("other", "filename", 0.6, filename)
    if re.search(boundary + r"(?:prf|fm\d+)(?:[._\-\s]|$)", lowered):
        return "preface", _evidence("preface", "filename", 0.6, filename)
    if re.search(boundary + r"in\d+_b(?:[._\-\s]|$)", lowered) and "index" in {x.lower() for x in sibling_types}:
        return "index", _evidence("index", "filename", 0.6, filename)
    match = _match(filename)
    if match:
        semantic_type, confidence = match
        return semantic_type, _evidence(semantic_type, "filename", confidence, filename)

    clean_title = title.strip()
    same_as_book = book_title and clean_title.casefold() == book_title.strip().casefold()
    if not clean_title or clean_title == "." or same_as_book:
        return "other", _evidence("other", "filename", 0.35, "No section title distinct from book title")
    return "chapter", _evidence("chapter", "spine", 0.4, "Default Phase 1 spine document")


def classify_from_title(
    title: str, resource: Resource, *, book_title: str | None = None
) -> tuple[str, list[SemanticEvidence]]:
    """Compatibility wrapper used by the Phase 1 planner."""
    return classify_section(title, resource, book_title=book_title)
