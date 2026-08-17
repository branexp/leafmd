"""EPUB 3 nav, EPUB 2 NCX, and guide landmarks."""

from __future__ import annotations

from collections.abc import Iterator

from lxml import etree

from leafmd.model.issues import IssueSeverity
from leafmd.model.publication import NavNode, Resource
from leafmd.model.report import ConversionReport
from leafmd.parse.hrefs import posix_join, split_fragment
from leafmd.parse.html import parse_document
from leafmd.parse.xmlutil import attr, child_text, local_name, parse_xml


def parse_nav_document(
    resource: Resource,
    report: ConversionReport,
) -> tuple[list[NavNode], list[NavNode]]:
    if resource.content is None:
        report.add(
            IssueSeverity.WARNING,
            "NAV_MISSING_BYTES",
            "Navigation document has no content",
            where=resource.href,
        )
        return [], []
    root = parse_xml(resource.content)
    toc: list[NavNode] = []
    landmarks: list[NavNode] = []
    for nav in _iter_named(root, "nav"):
        nav_type = (attr(nav, "type", "{http://www.idpf.org/2007/ops}type") or "").lower()
        classes = (attr(nav, "class") or "").split()
        epub_types = {part.lower() for part in (attr(nav, "{http://www.idpf.org/2007/ops}type") or "").split()}
        kind = "toc"
        if "landmarks" in epub_types or "landmarks" in classes or nav_type == "landmarks":
            kind = "landmarks"
        elif "page-list" in epub_types or "page-list" in classes or nav_type == "page-list":
            continue
        ol = next((child for child in nav if local_name(child.tag) == "ol"), None)
        if ol is None:
            continue
        nodes = _parse_nav_list(ol, resource.href, kind)
        if kind == "landmarks":
            landmarks.extend(nodes)
        else:
            toc.extend(nodes)
    if not toc:
        report.add(
            IssueSeverity.WARNING,
            "NAV_EMPTY_TOC",
            "Navigation document has no toc entries",
            where=resource.href,
        )
    return toc, landmarks


def parse_ncx(
    resource: Resource,
    report: ConversionReport,
) -> list[NavNode]:
    if resource.content is None:
        report.add(
            IssueSeverity.WARNING,
            "NCX_MISSING_BYTES",
            "NCX has no content",
            where=resource.href,
        )
        return []
    try:
        root = parse_xml(resource.content)
    except Exception as exc:  # noqa: BLE001 - recover from empty/malformed NCX
        report.add(
            IssueSeverity.WARNING,
            "NCX_MALFORMED",
            f"Could not parse NCX: {exc}",
            where=resource.href,
        )
        return []
    nav_map = next((node for node in root.iter() if local_name(node.tag) == "navMap"), None)
    if nav_map is None:
        report.add(IssueSeverity.WARNING, "NCX_EMPTY", "NCX has no navMap", where=resource.href)
        return []
    return [
        node
        for child in nav_map
        if local_name(child.tag) == "navPoint"
        for node in [_parse_nav_point(child, resource.href)]
        if node is not None
    ]


def guide_to_nodes(guide: list[tuple[str, str, str]]) -> list[NavNode]:
    return [
        NavNode(title=title or ref_type or href, href=href, kind="guide", semantic_type=ref_type or None)
        for title, href, ref_type in guide
    ]


def parse_html_toc(resource: Resource) -> list[NavNode]:
    """Collect in-document table-of-contents links when EPUB nav is missing."""
    if resource.content is None:
        return []
    try:
        root = parse_document(resource.content)
    except Exception:  # noqa: BLE001 - malformed HTML TOC is non-fatal
        return []
    seen: set[tuple[str, str | None]] = set()
    nodes: list[NavNode] = []
    for node in root.iter():
        if local_name(getattr(node, "tag", "")) != "a":
            continue
        href = attr(node, "href")
        title = child_text(node).strip()
        if not href or not title:
            continue
        from urllib.parse import urlparse

        parsed = urlparse(href)
        if parsed.scheme or parsed.netloc:
            continue
        abs_href = posix_join(resource.href, href)
        path, fragment = split_fragment(abs_href)
        if path == resource.href and not fragment:
            continue
        key = (path, fragment)
        if key in seen:
            continue
        seen.add(key)
        nodes.append(NavNode(title=title, href=abs_href, kind="html-toc"))
    return nodes


def flatten_nav(nodes: list[NavNode]) -> list[NavNode]:
    out: list[NavNode] = []

    def walk(items: list[NavNode]) -> None:
        for item in items:
            out.append(item)
            if item.children:
                walk(list(item.children))

    walk(nodes)
    return out


def _parse_nav_list(ol: etree._Element, base_href: str, kind: str) -> list[NavNode]:
    nodes: list[NavNode] = []
    for li in ol:
        if local_name(li.tag) != "li":
            continue
        anchor = next((child for child in li if local_name(child.tag) in {"a", "span"}), None)
        title = child_text(anchor) if anchor is not None else child_text(li)
        href = None
        semantic = None
        if anchor is not None:
            raw_href = attr(anchor, "href")
            if raw_href:
                href = posix_join(base_href, raw_href)
            semantic = attr(anchor, "{http://www.idpf.org/2007/ops}type")
        child_ol = next((child for child in li if local_name(child.tag) == "ol"), None)
        children = tuple(_parse_nav_list(child_ol, base_href, kind)) if child_ol is not None else ()
        nodes.append(
            NavNode(
                title=title or "Untitled",
                href=href,
                kind=kind if kind != "landmarks" else "landmark",
                semantic_type=semantic,
                children=children,
            )
        )
    return nodes


def _parse_nav_point(point: etree._Element, base_href: str) -> NavNode | None:
    label = ""
    href = None
    children: list[NavNode] = []
    for child in point:
        name = local_name(child.tag)
        if name == "navLabel":
            label = child_text(child)
        elif name == "content":
            src = attr(child, "src")
            if src:
                href = posix_join(base_href, src)
        elif name == "navPoint":
            nested = _parse_nav_point(child, base_href)
            if nested is not None:
                children.append(nested)
    if not label and not href:
        return None
    return NavNode(title=label or "Untitled", href=href, kind="ncx", children=tuple(children))


def _iter_named(root: etree._Element, name: str) -> Iterator[etree._Element]:
    for node in root.iter():
        if local_name(node.tag) == name:
            yield node
