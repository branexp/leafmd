"""Replace safe image occurrences with recovered semantic DOM content."""

from __future__ import annotations

from copy import deepcopy

from lxml import etree

from leafmd.model.images import ImageAnalysis, ImageBlock, ImageBlockKind, ImageDecision
from leafmd.model.issues import IssueSeverity
from leafmd.model.report import ConversionReport
from leafmd.parse.hrefs import posix_join, split_fragment
from leafmd.parse.xmlutil import attr, local_name

_DANGEROUS_TABLE_TAGS = frozenset({"script", "style", "iframe", "object", "embed", "form", "svg"})
_ALLOWED_TABLE_TAGS = frozenset(
    {
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
        "caption",
        "colgroup",
        "col",
        "b",
        "strong",
        "i",
        "em",
        "br",
        "code",
        "sub",
        "sup",
        "math",
    }
)
_CAPTION_LABELS = frozenset({"table_title", "table_caption", "figure_title", "figure_caption", "figure_table_title"})


def apply_image_conversions(
    root: etree._Element,
    source_href: str,
    analyses: dict[str, ImageAnalysis],
    report: ConversionReport,
) -> None:
    """Apply safe image replacements before leafmd rewrites source asset hrefs."""

    for image in [node for node in root.iter() if local_name(getattr(node, "tag", "")) == "img"]:
        src = attr(image, "src")
        if not src or src.startswith(("http://", "https://", "data:")):
            continue
        joined, _fragment = split_fragment(posix_join(source_href, src))
        analysis = analyses.get(joined)
        if analysis is None or analysis.decision is not ImageDecision.REPLACE:
            continue

        blocks = analysis.blocks
        if _has_publisher_caption(image):
            blocks = tuple(block for block in blocks if block.label not in _CAPTION_LABELS)
        if not blocks:
            continue

        if _is_inline_occurrence(image):
            if len(blocks) == 1 and blocks[0].kind is ImageBlockKind.FORMULA:
                replacement = _formula_element(blocks[0].content, inline=True)
                _replace_node(image, [replacement], preserve_id=True)
                report.stats.image_replacements += 1
                report.add(
                    IssueSeverity.INFO,
                    "IMAGE_CONVERTED",
                    "Replaced inline formula image with LaTeX",
                    where=joined,
                )
            else:
                report.add(
                    IssueSeverity.INFO,
                    "IMAGE_PRESERVED_CONTEXT",
                    "Preserved Markdown-representable image because its inline context cannot safely contain "
                    "recovered blocks",
                    where=joined,
                )
            continue

        replacements = _blocks_to_elements(blocks)
        if replacements is None:
            report.add(
                IssueSeverity.WARNING,
                "IMAGE_CONVERSION_UNSAFE",
                "Recovered image content could not be safely converted to DOM; preserved image",
                where=joined,
            )
            continue

        parent = image.getparent()
        if parent is not None and local_name(parent.tag) == "p" and _only_meaningful_child(parent, image):
            _replace_node(parent, replacements, preserve_id=True)
        else:
            _replace_node(image, replacements, preserve_id=True)
        report.stats.image_replacements += 1
        report.add(
            IssueSeverity.INFO,
            "IMAGE_CONVERTED",
            f"Replaced image with recovered semantic content via {analysis.backend}",
            where=joined,
        )


def _blocks_to_elements(blocks: tuple[ImageBlock, ...]) -> list[etree._Element] | None:
    out: list[etree._Element] = []
    for block in blocks:
        if block.kind is ImageBlockKind.TEXT:
            element = etree.Element("p")
            element.text = block.content
            out.append(element)
        elif block.kind is ImageBlockKind.FORMULA:
            out.append(_formula_element(block.content, inline=False))
        elif block.kind is ImageBlockKind.TABLE:
            table = _safe_table(block.content)
            if table is None:
                return None
            out.append(table)
    return out or None


def _formula_element(formula: str, *, inline: bool) -> etree._Element:
    element = etree.Element("span" if inline else "p")
    element.text = f"${formula}$" if inline else f"$${formula}$$"
    return element


def _safe_table(html: str) -> etree._Element | None:
    try:
        parsed = etree.fromstring(
            html.encode("utf-8"), parser=etree.HTMLParser(recover=True, no_network=True, huge_tree=False)
        )
    except (etree.XMLSyntaxError, ValueError):
        return None
    source = next((node for node in parsed.iter() if local_name(getattr(node, "tag", "")) == "table"), None)
    if source is None:
        return None
    table = deepcopy(source)
    for node in list(table.iter()):
        tag = local_name(getattr(node, "tag", "")).lower()
        if not tag:
            continue
        if _has_math_ancestor(node):
            continue
        if tag in _DANGEROUS_TABLE_TAGS:
            _drop_node(node)
            continue
        if tag not in _ALLOWED_TABLE_TAGS:
            _unwrap_node(node)
            continue
        if tag == "math":
            continue
        for raw_name in list(node.attrib):
            name = local_name(raw_name).lower()
            if tag in {"th", "td"} and name in {"rowspan", "colspan"}:
                value = (node.get(raw_name) or "").strip()
                if value.isdigit() and 1 <= int(value) <= 1000:
                    continue
            del node.attrib[raw_name]
    return table


_PHRASING_ONLY_PARENTS = frozenset(
    {
        "span",
        "a",
        "em",
        "strong",
        "b",
        "i",
        "label",
        "cite",
        "abbr",
        "dfn",
        "kbd",
        "samp",
        "var",
        "mark",
        "time",
        "bdi",
        "bdo",
        "ruby",
        "rp",
        "rt",
    }
)
_FLOW_PARENTS = frozenset(
    {
        "p",
        "div",
        "section",
        "article",
        "aside",
        "main",
        "header",
        "footer",
        "blockquote",
        "li",
        "td",
        "th",
        "dd",
        "dt",
        "caption",
    }
)


def _is_inline_occurrence(image: etree._Element) -> bool:
    parent = image.getparent()
    if parent is None:
        return True
    parent_tag = local_name(parent.tag).lower()
    if parent_tag == "figure":
        return False
    if parent_tag in _PHRASING_ONLY_PARENTS:
        return True
    if parent_tag in _FLOW_PARENTS:
        return not _only_meaningful_child(parent, image)
    return False


def _only_meaningful_child(parent: etree._Element, child: etree._Element) -> bool:
    if (parent.text or "").strip() or (child.tail or "").strip():
        return False
    return all(node is child or local_name(getattr(node, "tag", "")) == "" for node in parent)


def _has_publisher_caption(image: etree._Element) -> bool:
    parent = image.getparent()
    if parent is not None and local_name(parent.tag).lower() == "figure":
        return any(local_name(getattr(node, "tag", "")).lower() == "figcaption" for node in parent)
    return False


def _replace_node(node: etree._Element, replacements: list[etree._Element], *, preserve_id: bool) -> None:
    parent = node.getparent()
    if parent is None or not replacements:
        return
    index = parent.index(node)
    node_id = attr(node, "id") if preserve_id else None
    if node_id and attr(replacements[0], "id") is None:
        replacements[0].set("id", node_id)
    replacements[-1].tail = node.tail
    parent.remove(node)
    for offset, replacement in enumerate(replacements):
        parent.insert(index + offset, replacement)


def _has_math_ancestor(node: etree._Element) -> bool:
    parent = node.getparent()
    while parent is not None:
        if local_name(getattr(parent, "tag", "")).lower() == "math":
            return True
        parent = parent.getparent()
    return False


def _drop_node(node: etree._Element) -> None:
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


def _unwrap_node(node: etree._Element) -> None:
    parent = node.getparent()
    if parent is None:
        return
    index = parent.index(node)
    if node.text:
        if index:
            previous = parent[index - 1]
            previous.tail = (previous.tail or "") + node.text
        else:
            parent.text = (parent.text or "") + node.text
    children = list(node)
    for child in children:
        node.remove(child)
        parent.insert(index, child)
        index += 1
    if node.tail:
        if index:
            previous = parent[index - 1]
            previous.tail = (previous.tail or "") + node.tail
        else:
            parent.text = (parent.text or "") + node.tail
    parent.remove(node)
