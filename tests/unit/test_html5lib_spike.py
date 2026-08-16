"""P2-4 characterization: what lxml recover keeps vs drops. html5lib is not a runtime dep."""

from __future__ import annotations

import pytest

from leafmd.parse.html import parse_document
from leafmd.parse.xmlutil import child_text, local_name

pytestmark = pytest.mark.differential


def _text_by_tag(data: bytes, tag: str) -> list[str]:
    root = parse_document(data)
    return [child_text(node) for node in root.iter() if local_name(node.tag) == tag]


def test_lxml_recovers_unclosed_paragraph() -> None:
    html = b"<html><body><h1>Broken</h1><p>Unclosed paragraph<div>nested</p></div></body></html>"
    texts = " ".join(_text_by_tag(html, "p") + _text_by_tag(html, "div") + _text_by_tag(html, "h1"))
    assert "Broken" in texts
    assert "Unclosed paragraph" in texts
    assert "nested" in texts


def test_lxml_does_not_expand_external_entity() -> None:
    html = b"""<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<html><body><p>&xxe;</p></body></html>
"""
    texts = " ".join(_text_by_tag(html, "p"))
    assert "root:" not in texts


def test_html5lib_optional_comparison() -> None:
    html5lib = pytest.importorskip("html5lib")
    raw = b"<html><body><p>Unclosed<div>nested</p></div></body></html>"
    lxml_root = parse_document(raw)
    lxml_text = " ".join(child_text(node) for node in lxml_root.iter() if local_name(node.tag) in {"p", "div"})
    parsed = html5lib.parse(raw, namespaceHTMLElements=False)
    html5_text = " ".join(
        "".join(node.itertext()).strip() for node in parsed.iter() if getattr(node, "tag", None) in {"p", "div"}
    )
    assert "Unclosed" in lxml_text
    assert "nested" in lxml_text
    assert "Unclosed" in html5_text
    assert "nested" in html5_text
