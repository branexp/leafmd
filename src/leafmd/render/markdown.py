"""XHTML → Leafmd Markdown via a markdownify subclass."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from lxml import etree
from markdownify import MarkdownConverter

from leafmd.model.section import OutputTarget, SectionPlan
from leafmd.parse.html import body_element
from leafmd.parse.xmlutil import attr, local_name


class LeafmdConverter(MarkdownConverter):
    """ATX headings, GFM-friendly tables, explicit anchors kept as raw HTML."""

    def convert_hN(self, n: int, el: Any, text: str, parent_tags: Any = None) -> str:
        text = text.strip()
        return f"{'#' * n} {text}\n\n" if text else ""

    def convert_a(self, el: Any, text: str, parent_tags: Any = None) -> str:
        href = el.get("href") if hasattr(el, "get") else None
        node_id = el.get("id") if hasattr(el, "get") else None
        if node_id and not href and not (text or "").strip():
            return f'<a id="{node_id}"></a>'
        convert_a = MarkdownConverter.convert_a  # type: ignore[attr-defined]
        return str(convert_a(self, el, text, parent_tags))

    def convert_table(self, el: Any, text: str, parent_tags: Any = None) -> str:
        if _is_simple_table(el):
            convert_table = MarkdownConverter.convert_table  # type: ignore[attr-defined]
            return str(convert_table(self, el, text, parent_tags))
        serialized = str(el)
        return f"\n{serialized}\n"

    def convert_math(self, el: Any, text: str, convert_as_inline: bool = False, **kwargs: Any) -> str:
        if hasattr(el, "decode"):
            return str(el.decode())
        return str(el)


def render_section(
    root: etree._Element,
    plan: SectionPlan,
    targets: dict[tuple[str, str | None], OutputTarget],
) -> str:
    body = body_element(root)
    _inject_explicit_anchors(body, plan, targets)
    converter = LeafmdConverter(
        heading_style="ATX",
        bullets="-",
        escape_asterisks=False,
        escape_underscores=False,
        wrap=False,
    )
    markdown = converter.convert_soup(_as_bs4(body)).strip() + "\n"
    return _frontmatter(plan) + markdown


def _frontmatter(plan: SectionPlan) -> str:
    sources = []
    for source in plan.sources:
        item = f'  - href: "{_yaml_escape(source.href)}"'
        if source.start_id:
            item += f"\n    fragment: {_yaml_escape(source.start_id)}"
        sources.append(item)
    source_block = "\n".join(sources) if sources else "  []"
    return (
        "---\n"
        f"id: {plan.id}\n"
        f'title: "{_yaml_escape(plan.title)}"\n'
        f"type: {plan.type}\n"
        f"order: {plan.order}\n"
        "source:\n"
        f"{source_block}\n"
        "---\n\n"
    )


def _yaml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _inject_explicit_anchors(
    body: etree._Element,
    plan: SectionPlan,
    targets: dict[tuple[str, str | None], OutputTarget],
) -> None:
    injected: set[tuple[str, str]] = set()
    for source in plan.sources:
        path = source.href.split("#", 1)[0]
        for node in list(body.iter()):
            node_id = attr(node, "id")
            if not node_id:
                continue
            source_key = (path, node_id)
            if source_key in injected:
                continue
            target = targets.get(source_key)
            if target is None or not target.anchor:
                continue
            injected.add(source_key)
            anchor = etree.Element("a")
            anchor.set("id", target.anchor)
            parent = node.getparent()
            if parent is None:
                body.insert(0, anchor)
            else:
                index = list(parent).index(node)
                parent.insert(index, anchor)


def _as_bs4(element: etree._Element) -> Any:
    from bs4 import BeautifulSoup

    html = etree.tostring(element, encoding="unicode", method="html")
    return BeautifulSoup(html, "html.parser")


def _is_simple_table(el: Any) -> bool:
    html = str(el)
    if "rowspan" in html or "colspan" in html:
        return False
    descendants = list(getattr(el, "descendants", []) or [])
    if not descendants and hasattr(el, "iter"):
        descendants = list(el.iter())
    for node in descendants:
        name = local_name(getattr(node, "name", None) or getattr(node, "tag", ""))
        if not name or name in {"table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption"}:
            continue
        return False
    return True


def serialize_body(root: etree._Element) -> bytes:
    buffer = BytesIO()
    buffer.write(etree.tostring(root, encoding="utf-8"))
    return buffer.getvalue()
