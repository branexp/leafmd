"""XHTML / HTML recovery parse."""

from __future__ import annotations

from lxml import etree

from leafmd.parse.xmlutil import HTML_PARSER, parse_xml


def parse_document(data: bytes) -> etree._Element:
    try:
        return parse_xml(data)
    except etree.XMLSyntaxError:
        return etree.fromstring(data, parser=HTML_PARSER)


def body_element(root: etree._Element) -> etree._Element:
    for node in root.iter():
        tag = node.tag
        name = tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""
        if name == "body":
            return node
    return root
