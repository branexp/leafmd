"""Analyze EPUB note references without rendering or owning target maps.

The analyzer deliberately returns facts and relationships only.  A renderer may
use the ``simple_local`` decisions to emit footnotes, while retaining ordinary
links for everything else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urldefrag, urlsplit

from lxml import etree

from leafmd.parse.xmlutil import attr, child_text, local_name


class NoteClass(StrEnum):
    SIMPLE_LOCAL = "simple_local"
    COMPLEX = "complex"
    AMBIGUOUS = "ambiguous"
    CROSS_DOCUMENT = "cross_document"


@dataclass(frozen=True)
class NoteRelationship:
    """An explicit source reference → definition relationship."""

    reference_id: str | None
    definition_id: str | None
    href: str | None
    label: str
    classification: NoteClass

    @property
    def simple_local(self) -> bool:
        return self.classification is NoteClass.SIMPLE_LOCAL


@dataclass(frozen=True)
class NoteAnalysis:
    """Complete, deterministic note analysis for one parsed document."""

    references: tuple[etree._Element, ...]
    definitions: tuple[etree._Element, ...]
    relationships: tuple[NoteRelationship, ...]

    @property
    def simple_local(self) -> tuple[NoteRelationship, ...]:
        return tuple(item for item in self.relationships if item.simple_local)

    @property
    def complex(self) -> tuple[NoteRelationship, ...]:
        return tuple(item for item in self.relationships if item.classification is NoteClass.COMPLEX)

    @property
    def ambiguous(self) -> tuple[NoteRelationship, ...]:
        return tuple(item for item in self.relationships if item.classification is NoteClass.AMBIGUOUS)

    @property
    def cross_document(self) -> tuple[NoteRelationship, ...]:
        return tuple(item for item in self.relationships if item.classification is NoteClass.CROSS_DOCUMENT)


_NOTE_REF = {"noteref", "doc-noteref"}
_NOTE_DEF = {"footnote", "doc-footnote", "endnote", "doc-endnote"}
_BLOCKS = {
    "address",
    "blockquote",
    "div",
    "dl",
    "fieldset",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "ol",
    "p",
    "pre",
    "table",
    "ul",
}
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def _tokens(node: etree._Element, *names: str) -> set[str]:
    values: list[str] = []
    for name in names:
        value = attr(node, name)
        # ``epub:type`` is namespace-expanded by lxml, while the helper's
        # local-name fallback intentionally handles unprefixed attributes.
        if value is None and name == "epub:type":
            value = next((candidate for key, candidate in node.attrib.items() if local_name(key) == "type"), None)
        if value:
            values.extend(value.lower().split())
    return set(values)


def _is_reference(node: etree._Element) -> bool:
    return bool(_tokens(node, "epub:type", "role") & _NOTE_REF)


def _is_definition(node: etree._Element) -> bool:
    return bool(_tokens(node, "epub:type", "role") & _NOTE_DEF)


def _id(node: etree._Element) -> str | None:
    return attr(node, "id", "xml:id")


def _href(node: etree._Element) -> str | None:
    value = attr(node, "href")
    if value and not value.startswith(("javascript:", "data:")):
        return value
    return None


def _fallback_reference(node: etree._Element) -> bool:
    """Publisher fallback: an anchor containing a superscript marker."""
    return local_name(node.tag) == "a" and any(local_name(child.tag) == "sup" for child in node.iterdescendants())


def _fallback_definition(node: etree._Element) -> bool:
    """Publisher fallback: an id-bearing note block with a link back to source."""
    if not _id(node) or local_name(node.tag) not in {"aside", "div", "li", "p", "section"}:
        return False
    if any(_is_reference(child) or _fallback_reference(child) for child in node.iterdescendants()):
        return False
    return any(
        local_name(child.tag) == "a" and _href(child) and ("#" in (_href(child) or ""))
        for child in node.iterdescendants()
    )


def _rich_definition(node: etree._Element) -> bool:
    return any(
        local_name(child.tag) in _BLOCKS or local_name(child.tag) in {"math", "ruby", "table"}
        for child in node.iterdescendants()
    )


def sanitize_label(source: str, identity: str | None = None, *, fallback: str = "fallback") -> str:
    """Return a stable GFM-compatible label, independent of encounter order."""
    value = f"{source}--{identity or fallback}" if source else (identity or fallback)
    value = value.lower().replace("%", " percent ")
    tokens = _TOKEN_RE.findall(value)
    return "note-" + "-".join(tokens)[:80] if tokens else "note-" + fallback


def _same_document(source_href: str, href: str | None) -> bool:
    if not href or href.startswith("#"):
        return True
    source = urldefrag(source_href)[0]
    target = urldefrag(href)[0]
    if not target:
        return True
    return posix_path(source) == posix_path(target)


def posix_path(value: str) -> str:
    return urlsplit(value).path


def _target_id(href: str | None) -> str | None:
    if not href:
        return None
    return urldefrag(href)[1] or None


def _definition_map(definitions: tuple[etree._Element, ...]) -> dict[str, etree._Element]:
    return {value: node for node in definitions if (value := _id(node)) is not None}


def analyze_notes(
    root: etree._Element,
    source_href: str = "",
    *,
    same_section: bool = True,
) -> NoteAnalysis:
    """Identify note nodes and classify their links conservatively.

    ``same_section`` is supplied by a section slicer when a source note and its
    reference are known to be in different generated sections.  It defaults to
    true for standalone document analysis.
    """
    refs = tuple(
        node for node in root.iter() if isinstance(node.tag, str) and (_is_reference(node) or _fallback_reference(node))
    )
    defs = tuple(
        node
        for node in root.iter()
        if isinstance(node.tag, str) and (_is_definition(node) or _fallback_definition(node))
    )
    by_id = _definition_map(defs)
    relationships: list[NoteRelationship] = []
    target_counts: dict[str, int] = {}
    for ref in refs:
        target = _target_id(_href(ref))
        if target:
            target_counts[target] = target_counts.get(target, 0) + 1
    for ref in refs:
        href = _href(ref)
        target = _target_id(href)
        definition = by_id.get(target) if target else None
        candidates = [definition] if definition is not None else []
        if target and definition is None:
            candidates = [node for node in defs if _id(node) == target]
        if not _same_document(source_href, href):
            classification = NoteClass.CROSS_DOCUMENT
            definition_id = target or (_id(candidates[0]) if candidates else None)
        elif len(candidates) != 1 or (target is not None and target_counts.get(target, 0) > 1):
            classification = NoteClass.AMBIGUOUS
            definition_id = target
        elif not same_section or _rich_definition(candidates[0]):
            classification = NoteClass.COMPLEX
            definition_id = _id(candidates[0])
        else:
            classification = NoteClass.SIMPLE_LOCAL
            definition_id = _id(candidates[0])
        identity = _id(ref) or target or child_text(ref)
        relationships.append(
            NoteRelationship(_id(ref), definition_id, href, sanitize_label(source_href, identity), classification)
        )
    return NoteAnalysis(refs, defs, tuple(relationships))


# Descriptive aliases make the transform convenient for callers using either
# terminology used by EPUB or the phase specification.
NoteKind = NoteClass
NoteDecision = NoteClass
