"""Merge consecutive XHTML documents belonging to one logical section."""

from __future__ import annotations

from copy import deepcopy

from lxml import etree

from leafmd.parse.html import body_element


def merge_documents(roots: list[etree._Element]) -> etree._Element:
    if not roots:
        raise ValueError("at least one document is required")
    result = deepcopy(roots[0])
    body = body_element(result)
    for root in roots[1:]:
        other = body_element(root)
        if other.text and other.text.strip():
            body.text = (body.text or "") + other.text
        for node in other:
            body.append(deepcopy(node))
    return result
