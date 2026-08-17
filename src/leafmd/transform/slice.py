"""Slice an XHTML document at chapter headings."""

from __future__ import annotations

from copy import deepcopy

from lxml import etree

from leafmd.parse.html import body_element
from leafmd.parse.xmlutil import attr, local_name


def slice_document(root: etree._Element, start_id: str | None = None, end_id: str | None = None) -> etree._Element:
    """Return a copy containing body content from ``start_id`` up to ``end_id``."""
    if not start_id and not end_id:
        return deepcopy(root)
    result = deepcopy(root)
    body = body_element(result)
    children = list(body)
    start = 0
    end = len(children)
    for index, node in enumerate(children):
        if attr(node, "id") == start_id:
            start = index
        if end_id and attr(node, "id") == end_id:
            end = index
            break
    for node in children[:start] + children[end:]:
        body.remove(node)
    return result


def heading_nodes(root: etree._Element) -> list[etree._Element]:
    body = body_element(root)
    return [node for node in body if local_name(getattr(node, "tag", "")) in {"h1", "h2"}]
