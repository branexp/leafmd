"""Conservative preservation and safety helpers for rich inline markup.

This module is deliberately a converter-side boundary, not a general-purpose
HTML sanitizer.  It keeps the structures for which Markdown has no faithful
representation (MathML, ruby, and bidirectional text) while removing active
content that must not be emitted by the converter.
"""

from __future__ import annotations

import re
from copy import deepcopy

from lxml import etree

from leafmd.parse.xmlutil import local_name

RICH_TAGS = frozenset({"math", "ruby", "rb", "rt", "rp", "bdi", "bdo"})
# These are removed rather than merely having their attributes changed: their
# contents can carry executable or externally active behavior.
_UNSAFE_TAGS = frozenset({"script", "iframe", "object", "embed", "form", "base", "applet", "portal", "svg"})
_URL_ATTRIBUTES = frozenset({"href", "src", "action", "formaction", "xlink:href", "poster", "cite", "background"})
_SAFE_SCHEMES = frozenset({"", "http", "https", "mailto"})
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
_SAFE_DIR = frozenset({"ltr", "rtl", "auto"})


def is_rich_element(node: etree._Element) -> bool:
    """Return whether *node* is a preserved MathML, ruby, or bidi element."""

    return local_name(getattr(node, "tag", "")).lower() in RICH_TAGS


def contains_rich_markup(root: etree._Element) -> bool:
    """Return whether a tree contains one of the markup families we preserve."""

    return any(is_rich_element(node) for node in root.iter())


def protected_rich_nodes(root: etree._Element) -> tuple[etree._Element, ...]:
    """Return rich nodes and descendants whose text must not be normalized.

    The containing paragraph is intentionally not included: ordinary prose
    around an equation or ruby annotation can still be normalized safely.
    """

    protected: list[etree._Element] = []
    for node in root.iter():
        if is_rich_element(node) or any(is_rich_element(parent) for parent in node.iterancestors()):
            protected.append(node)
    return tuple(protected)


def is_text_normalization_protected(node: etree._Element) -> bool:
    """Return whether text directly owned by *node* is rich markup text."""

    return is_rich_element(node) or any(is_rich_element(parent) for parent in node.iterancestors())


def sanitize_rich_tree(root: etree._Element) -> etree._Element:
    """Remove active content and unsafe attributes in-place, returning *root*.

    Safe MathML structure/attributes, ruby annotations, directional elements,
    Unicode directional marks, and ordinary relative links are left intact.
    Unsafe URL attributes are removed in their entirety; this helper does not
    rewrite links or assets, which remains the responsibility of ``links.py``.
    """

    for node in list(root.iter()):
        if not isinstance(node.tag, str):
            continue
        tag = local_name(node.tag).lower()
        if tag in _UNSAFE_TAGS:
            _remove_node(node)
            continue
        _sanitize_attributes(node)
    return root


def preserve_rich_markup(root: etree._Element) -> etree._Element:
    """Copy and sanitize a tree while preserving safe rich markup."""

    return sanitize_rich_tree(deepcopy(root))


def _remove_node(node: etree._Element) -> None:
    parent = node.getparent()
    if parent is None:
        return
    tail = node.tail or ""
    previous = node.getprevious()
    if previous is not None:
        previous.tail = (previous.tail or "") + tail
    else:
        parent.text = (parent.text or "") + tail
    parent.remove(node)


def _sanitize_attributes(node: etree._Element) -> None:
    for raw_name, value in list(node.attrib.items()):
        name = local_name(raw_name).lower()
        if name.startswith("on") or name in {"style", "srcdoc"}:
            del node.attrib[raw_name]
            continue
        if name == "dir":
            if value is None or value.strip().lower() not in _SAFE_DIR:
                del node.attrib[raw_name]
            else:
                node.set(raw_name, value.strip().lower())
            continue
        if name in _URL_ATTRIBUTES and value is not None and not _safe_url(value):
            del node.attrib[raw_name]


def _safe_url(value: str) -> bool:
    candidate = value.strip()
    # Control characters and leading whitespace are normalized by browsers
    # before scheme checks, so reject them instead of attempting to canonicalize.
    if any(char in candidate[:32] for char in "\r\n\t"):
        return False
    match = _SCHEME.match(candidate)
    return match is None or candidate[: match.end() - 1].lower() in _SAFE_SCHEMES


# Descriptive aliases for callers that prefer the operation rather than the
# implementation detail in the function name.
sanitize_rich_content = sanitize_rich_tree
copy_safe_rich_tree = preserve_rich_markup
