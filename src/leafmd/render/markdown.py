"""XHTML → Leafmd Markdown via a markdownify subclass."""

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from typing import Any, cast

from lxml import etree
from markdownify import MarkdownConverter

from leafmd.model.section import OutputTarget, SectionPlan
from leafmd.parse.hrefs import posix_join, split_fragment
from leafmd.parse.html import body_element
from leafmd.parse.xmlutil import attr, local_name
from leafmd.transform.notes import analyze_notes
from leafmd.transform.rich import is_rich_element, sanitize_rich_tree
from leafmd.transform.tables import classify_table
from leafmd.transform.textnorm import normalize_text, promote_leading_bold_title


class LeafmdConverter(MarkdownConverter):
    """ATX headings, conservative tables, and explicit anchors kept as HTML."""

    def __init__(self, *args: Any, protected: dict[str, str] | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.protected = protected if protected is not None else {}

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

    def convert_span(self, el: Any, text: str, parent_tags: Any = None) -> str:
        token = el.get("data-leafmd-token") if hasattr(el, "get") else None
        if token:
            return str(token)
        return text

    def convert_table(self, el: Any, text: str, parent_tags: Any = None) -> str:
        source = _soup_to_lxml(el)
        decision = classify_table(source)
        if decision.gfm_safe:
            # markdownify otherwise treats caption as an extra row.  The
            # decision's caption is emitted exactly once, immediately before.
            table = deepcopy(decision.normalized_table)
            for child in list(table):
                if local_name(child.tag) == "caption":
                    table.remove(child)
            soup = _as_bs4(table)
            rendered = _gfm_table(self, soup.find("table"))
            caption_text = decision.caption.text if decision.caption is not None else ""
            return "\n\n" + (caption_text + "\n\n" if caption_text else "") + rendered + "\n\n"
        token = _protected_token(
            self.protected, etree.tostring(decision.source_table, encoding="unicode", with_tail=False)
        )
        return token

    def convert_math(self, el: Any, text: str, convert_as_inline: bool = False, **kwargs: Any) -> str:
        return _protected_token(self.protected, str(el))

    def convert_ruby(self, el: Any, text: str, parent_tags: Any = None) -> str:
        return _protected_token(self.protected, str(el))

    def convert_rb(self, el: Any, text: str, parent_tags: Any = None) -> str:
        return _protected_token(self.protected, str(el))

    def convert_rt(self, el: Any, text: str, parent_tags: Any = None) -> str:
        return _protected_token(self.protected, str(el))

    def convert_rp(self, el: Any, text: str, parent_tags: Any = None) -> str:
        return _protected_token(self.protected, str(el))

    def convert_bdi(self, el: Any, text: str, parent_tags: Any = None) -> str:
        return _protected_token(self.protected, str(el))

    def convert_bdo(self, el: Any, text: str, parent_tags: Any = None) -> str:
        return _protected_token(self.protected, str(el))


def render_section(
    root: etree._Element,
    plan: SectionPlan,
    targets: dict[tuple[str, str | None], OutputTarget],
) -> str:
    body = body_element(root)
    _inject_explicit_anchors(body, plan, targets)
    sanitize_rich_tree(body)
    protected: dict[str, str] = {}
    footnotes = _prepare_rich_and_notes(body, plan, targets, protected)
    _prepare_caption_wrappers(body)
    converter = LeafmdConverter(
        heading_style="ATX",
        bullets="-",
        escape_asterisks=False,
        escape_underscores=False,
        wrap=False,
        protected=protected,
    )
    markdown = converter.convert_soup(_as_bs4(body)).strip()
    markdown = promote_leading_bold_title(normalize_text(markdown))
    for token, value in protected.items():
        markdown = markdown.replace(token, value)
    if footnotes:
        markdown = markdown.rstrip() + "\n\n" + "\n".join(f"[^{label}]: {text}" for label, text in footnotes)
    markdown = markdown.rstrip() + "\n"
    return _frontmatter(plan) + markdown


def _prepare_rich_and_notes(
    body: etree._Element,
    plan: SectionPlan,
    targets: dict[tuple[str, str | None], OutputTarget],
    protected: dict[str, str],
) -> list[tuple[str, str]]:
    # Replace rich nodes with inert placeholders before BeautifulSoup parsing;
    # this prevents markdownify and text normalization from touching them.
    for node in list(body.iter()):
        if node is body or not is_rich_element(node):
            continue
        if any(is_rich_element(parent) for parent in node.iterancestors()):
            continue
        _replace_with_token(node, etree.tostring(node, encoding="unicode", with_tail=False), protected)
    # Link rewriting happens before rendering, so analyze a copy with known
    # target-map links restored to source identities.  The output tree remains
    # rewritten for complex/cross-document notes; only simple-local references
    # are replaced below.
    analysis_body = deepcopy(body)
    _restore_source_note_hrefs(analysis_body, plan, targets)
    source = plan.sources[0].href.split("#", 1)[0] if plan.sources else ""
    analysis = analyze_notes(analysis_body, source)
    original_by_analysis_node = dict(zip(analysis_body.iter(), body.iter(), strict=True))
    definitions: dict[str, etree._Element] = {}
    for rel in analysis.simple_local:
        if rel.definition_id:
            definition_node = _find_id(body, rel.definition_id)
            if definition_node is not None:
                definitions[rel.definition_id] = definition_node
    footnotes: list[tuple[str, str]] = []
    for rel in analysis.simple_local:
        reference = next(
            (
                original_by_analysis_node[reference_node]
                for reference_node, candidate in zip(analysis.references, analysis.relationships, strict=True)
                if candidate is rel
            ),
            None,
        )
        if reference is not None:
            _replace_with_token(reference, f"[^{rel.label}]", protected)
        definition = definitions.get(rel.definition_id or "")
        if definition is not None:
            footnotes.append((rel.label, " ".join("".join(definition.itertext()).split())))
            parent = definition.getparent()
            if parent is not None:
                parent.remove(definition)
    return footnotes


def _restore_source_note_hrefs(
    root: etree._Element,
    plan: SectionPlan,
    targets: dict[tuple[str, str | None], OutputTarget],
) -> None:
    output_path = plan.output_path or ""
    plan_paths = {split_fragment(source.href)[0] for source in plan.sources}
    reverse: dict[tuple[str, str], tuple[str, str]] = {}
    for (source_path, source_id), target in targets.items():
        if source_id is not None and target.anchor is not None:
            reverse[(target.path, target.anchor)] = (source_path, source_id)
    for node in root.iter():
        href = attr(node, "href")
        if not href:
            continue
        joined = posix_join(output_path, href)
        path, fragment = split_fragment(joined)
        if fragment is None:
            continue
        source_target = reverse.get((path, fragment))
        if source_target is not None:
            source_path, source_id = source_target
            node.set("href", f"#{source_id}" if source_path in plan_paths else f"{source_path}#{source_id}")


def _replace_with_token(node: etree._Element, value: str, protected: dict[str, str]) -> None:
    token = _protected_token(protected, value)
    replacement = etree.Element("span")
    replacement.set("data-leafmd-token", token)
    parent = node.getparent()
    if parent is None:
        return
    index = parent.index(node)
    replacement.tail = node.tail
    parent.remove(node)
    parent.insert(index, replacement)


def _protected_token(protected: dict[str, str], value: str) -> str:
    token = f"LEAFMD_PROTECTED_{len(protected):08d}_END"
    protected[token] = value
    return token


def _find_id(root: etree._Element, value: str) -> etree._Element | None:
    return next((node for node in root.iter() if attr(node, "id") == value), None)


def _prepare_caption_wrappers(body: etree._Element) -> None:
    for table in list(body.iter("table")):
        decision = classify_table(table)
        if decision.caption is None or decision.caption.source != "publisher-wrapper" or not decision.gfm_safe:
            continue
        parent = table.getparent()
        if parent is None:
            continue
        for sibling in list(parent):
            if (
                sibling is not table
                and attr(sibling, "class")
                and set((attr(sibling, "class") or "").split()) & {"Caption", "caption", "TableCaption"}
            ):
                parent.remove(sibling)


def _gfm_table(converter: LeafmdConverter, table: Any) -> str:
    rows: list[list[str]] = []
    for row in table.find_all("tr", recursive=True):
        cells = row.find_all(["th", "td"], recursive=False)
        values = []
        for cell in cells:
            from bs4 import BeautifulSoup

            value = (
                converter.convert_soup(BeautifulSoup(cell.decode_contents(), "html.parser")).strip().replace("|", "\\|")
            )
            values.append(" ".join(value.split()))
        rows.append(values)
    if not rows:
        return ""
    width = len(rows[0])
    lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join("---" for _ in range(width)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _soup_to_lxml(element: Any) -> etree._Element:
    root = etree.fromstring(str(element).encode("utf-8"), parser=etree.HTMLParser())
    return cast(etree._Element, root.xpath(".//table")[0])


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
    body: etree._Element, plan: SectionPlan, targets: dict[tuple[str, str | None], OutputTarget]
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
                parent.insert(list(parent).index(node), anchor)


def _as_bs4(element: etree._Element) -> Any:
    from bs4 import BeautifulSoup

    return BeautifulSoup(etree.tostring(element, encoding="unicode", method="html"), "html.parser")


def serialize_body(root: etree._Element) -> bytes:
    buffer = BytesIO()
    buffer.write(etree.tostring(root, encoding="utf-8"))
    return buffer.getvalue()
