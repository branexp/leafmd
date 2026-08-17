"""Conservative table classification and normalization.

This module deliberately stops at a typed tree decision.  Rendering (including
Markdown syntax) belongs to the renderer; a caller can use ``normalized_table``
for a GFM decision or retain ``source_table`` for a raw-HTML decision.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum

from lxml import etree

from leafmd.parse.xmlutil import local_name


class TableKind(StrEnum):
    """The two representations a table may safely use downstream."""

    GFM = "gfm"
    RAW_HTML = "raw-html"


@dataclass(frozen=True)
class CaptionMetadata:
    """Caption information retained independently of table classification."""

    text: str
    element: etree._Element
    source: str = "caption"


@dataclass(frozen=True)
class TableDecision:
    """A deterministic, non-rendering table normalization result."""

    kind: TableKind
    reason: str
    rows: int
    columns: int
    caption: CaptionMetadata | None
    source_table: etree._Element
    normalized_table: etree._Element

    @property
    def gfm_safe(self) -> bool:
        return self.kind is TableKind.GFM

    @property
    def preserve_as_raw_html(self) -> bool:
        return self.kind is TableKind.RAW_HTML


_BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "div",
    "dl",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "ul",
}
# These tags have an inline representation and are safe for a later Markdown renderer.
_INLINE_TAGS = {
    "a",
    "abbr",
    "b",
    "br",
    "cite",
    "code",
    "del",
    "em",
    "i",
    "ins",
    "kbd",
    "mark",
    "q",
    "s",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "time",
    "u",
    "var",
}


def classify_table(table: etree._Element) -> TableDecision:
    """Classify *table* without mutating it.

    ``normalized_table`` is a deep copy.  Only ``.SimplePara`` wrappers are
    unwrapped, and only when the table passes all safety checks.  Spans are
    never expanded or flattened.
    """

    source = table
    normalized = deepcopy(table)
    caption = _caption_metadata(table)
    rows = _rows(table)
    row_count = len(rows)
    widths = [len(_cells(row)) for row in rows]
    columns = max(widths, default=0)

    reason = _unsafe_reason(table, rows, widths)
    if reason is None:
        _unwrap_simple_para(normalized)
        return TableDecision(TableKind.GFM, "rectangular-inline-safe", row_count, columns, caption, source, normalized)
    return TableDecision(TableKind.RAW_HTML, reason, row_count, columns, caption, source, normalized)


def normalize_table(table: etree._Element) -> TableDecision:
    """Alias emphasizing that classification also returns a normalized tree."""

    return classify_table(table)


def _rows(table: etree._Element) -> list[etree._Element]:
    return [node for node in table.iter() if local_name(getattr(node, "tag", "")) == "tr"]


def _cells(row: etree._Element) -> list[etree._Element]:
    return [node for node in row if local_name(getattr(node, "tag", "")) in {"td", "th"}]


def _unsafe_reason(table: etree._Element, rows: list[etree._Element], widths: list[int]) -> str | None:
    if not rows:
        return "missing-rows"
    if any(local_name(getattr(node, "tag", "")) == "table" for node in table.iter() if node is not table):
        return "nested-table"
    if any("rowspan" in cell.attrib or "colspan" in cell.attrib for row in rows for cell in _cells(row)):
        return "rowspan-or-colspan"
    if len(set(widths)) != 1 or not widths[0]:
        return "non-rectangular"
    header = rows[0]
    header_cells = _cells(header)
    if not all(local_name(cell.tag) == "th" for cell in header_cells):
        return "missing-predictable-header"
    if any(local_name(cell.tag) == "th" for row in rows[1:] for cell in _cells(row)):
        return "ambiguous-header"
    for row in rows:
        for cell in _cells(row):
            if not _inline_safe(cell):
                return "non-inline-safe-cell-content"
    return None


def _inline_safe(cell: etree._Element) -> bool:
    for node in cell.iterdescendants():
        tag = local_name(getattr(node, "tag", ""))
        if tag in _BLOCK_TAGS:
            if "SimplePara" not in _class_tokens(node):
                return False
            continue
        if tag in {
            "img",
            "svg",
            "math",
            "ruby",
            "rb",
            "rt",
            "rp",
            "script",
            "iframe",
            "object",
            "video",
            "audio",
            "input",
        }:
            return False
        if tag not in _INLINE_TAGS and tag:
            return False
    return True


def _class_tokens(element: etree._Element) -> set[str]:
    return set((element.get("class") or "").split())


def _caption_metadata(table: etree._Element) -> CaptionMetadata | None:
    direct = next((child for child in table if local_name(getattr(child, "tag", "")) == "caption"), None)
    if direct is not None:
        return CaptionMetadata(_text(direct), deepcopy(direct), "caption")
    parent = table.getparent()
    if parent is not None:
        siblings = list(parent)
        index = siblings.index(table)
        for sibling in siblings[max(0, index - 1) : index] + siblings[index + 1 : index + 2]:
            if _class_tokens(sibling) & {"Caption", "caption", "TableCaption"}:
                return CaptionMetadata(_text(sibling), deepcopy(sibling), "publisher-wrapper")
    return None


def _text(element: etree._Element) -> str:
    return re.sub(r"\s+", " ", "".join(element.itertext())).strip()


def _unwrap_simple_para(root: etree._Element) -> None:
    for wrapper in list(root.iter()):
        if wrapper is root or "SimplePara" not in _class_tokens(wrapper):
            continue
        parent = wrapper.getparent()
        if parent is None:
            continue
        index = parent.index(wrapper)
        if wrapper.text:
            if index:
                previous = parent[index - 1]
                previous.tail = (previous.tail or "") + wrapper.text
            else:
                parent.text = (parent.text or "") + wrapper.text
        children = list(wrapper)
        for child in children:
            parent.insert(index, child)
            index += 1
        if wrapper.tail:
            if index:
                previous = parent[index - 1]
                previous.tail = (previous.tail or "") + wrapper.tail
            else:
                parent.text = (parent.text or "") + wrapper.tail
        parent.remove(wrapper)
