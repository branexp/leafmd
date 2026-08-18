"""Safe XML helpers. Entity resolution and network access stay off."""

from __future__ import annotations

from lxml import etree

PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    dtd_validation=False,
    load_dtd=False,
    huge_tree=False,
    recover=True,
)

HTML_PARSER = etree.HTMLParser(recover=True, no_network=True, huge_tree=False)


def parse_xml(data: bytes) -> etree._Element:
    return etree.fromstring(data, parser=PARSER)


def parse_html(data: bytes) -> etree._Element:
    return etree.fromstring(data, parser=HTML_PARSER)


def local_name(tag: object) -> str:
    """Return the un-namespaced tag name. Non-string tags (comments, entities) are empty."""
    if not isinstance(tag, str):
        return ""
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def child_text(element: etree._Element | None) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def attr(element: etree._Element, *names: str) -> str | None:
    for name in names:
        value = element.get(name)
        if isinstance(value, str) and value:
            return value
        if "}" not in name:
            for key, candidate in element.attrib.items():
                if local_name(key) == name and isinstance(candidate, str) and candidate:
                    return candidate
    return None
