"""Plan logical sections from spine documents and navigation evidence."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree

from leafmd.model.issues import IssueSeverity
from leafmd.model.publication import NormalizedPublication, Resource, SpineEntry
from leafmd.model.report import ConversionReport
from leafmd.model.section import SectionPlan, SourceRange
from leafmd.parse.hrefs import split_fragment
from leafmd.parse.html import parse_document
from leafmd.parse.navigation import flatten_nav
from leafmd.parse.xmlutil import child_text, local_name
from leafmd.semantics.classify import classify_section
from leafmd.transform.slug import slugify

CONTENT_TYPES = {"application/xhtml+xml", "text/html", "application/xml", "text/xml"}


@dataclass(frozen=True)
class _NavInfo:
    title: str
    href: str
    fragment: str | None
    semantic_type: str | None
    source: str


def plan_sections(publication: NormalizedPublication, report: ConversionReport) -> list[SectionPlan]:
    infos = _nav_infos(publication)
    by_path: dict[str, list[_NavInfo]] = {}
    for info in infos:
        by_path.setdefault(split_fragment(info.href)[0], []).append(info)
    spine = [
        e
        for e in publication.spine
        if _resource_for_entry(publication, e) is not None and _convertible(_resource_for_entry(publication, e))
    ]
    plans: list[SectionPlan] = []
    index = 0
    pos = 0
    sibling_types: list[str] = []
    while pos < len(spine):
        entry = spine[pos]
        resource = _resource_for_entry(publication, entry)
        assert resource is not None
        if not entry.linear:
            report.add(
                IssueSeverity.INFO,
                "PLAN_NONLINEAR",
                "Included non-linear spine item as its own file",
                where=resource.href,
            )
        path = resource.href
        entries = by_path.get(path, [])
        # Multiple fragment navigation targets into one file define chapter slices.
        if len(entries) > 1 and all(item.fragment for item in entries):
            root = _parse(resource)
            headings = _heading_data(root)
            selected = [item for item in entries if item.fragment in headings]
            if len(selected) > 1:
                for n, item in enumerate(selected):
                    index += 1
                    end_id = selected[n + 1].fragment if n + 1 < len(selected) else None
                    fragment = item.fragment
                    assert fragment is not None
                    title = item.title or headings.get(fragment, "") or resource.id
                    plans.append(_make_plan(publication, resource, item, title, index, sibling_types, end_id=end_id))
                    sibling_types.append(plans[-1].type)
                pos += 1
                continue
        # A single navigation entry owns following spine documents until the next
        # independently navigated document (the common split-chapter pattern).
        group = [resource]
        if len(entries) == 1 and entry.linear:
            look = pos + 1
            while look < len(spine):
                nxt = _resource_for_entry(publication, spine[look])
                if nxt is None or by_path.get(nxt.href) or not spine[look].linear:
                    break
                group.append(nxt)
                look += 1
        index += 1
        nav_item: _NavInfo | None = entries[0] if entries else None
        title = (nav_item.title if nav_item else None) or _heading_fallback(resource.content) or resource.id
        plan = _make_plan(publication, resource, nav_item, title, index, sibling_types, extra=group[1:])
        plans.append(plan)
        sibling_types.append(plan.type)
        pos += len(group)
    if not plans:
        report.add(IssueSeverity.FATAL, "PLAN_NO_SECTIONS", "No convertible content documents in the spine")
    return plans


def _make_plan(
    publication: NormalizedPublication,
    resource: Resource,
    item: _NavInfo | None,
    title: str,
    order: int,
    sibling_types: list[str],
    *,
    end_id: str | None = None,
    extra: list[Resource] | None = None,
) -> SectionPlan:
    headings = _heading_texts(resource.content)
    semantic_type, evidence = classify_section(
        title,
        resource,
        nav_label=item.title if item else None,
        ncx_title=next(
            (x.title for x in _nav_infos(publication, source="ncx") if split_fragment(x.href)[0] == resource.href),
            None,
        ),
        headings=headings,
        book_title=publication.metadata.title,
        sibling_types=sibling_types,
    )
    start_fragment = item.fragment if item else None
    source_href = resource.href + (f"#{start_fragment}" if start_fragment else "")
    sources = [SourceRange(href=source_href, start_id=start_fragment, end_id=end_id)]
    for other in extra or []:
        sources.append(SourceRange(href=other.href))
    filename = f"{order:03d}-{semantic_type}-{slugify(title)}.md"
    return SectionPlan(
        f"sec-{order:03d}",
        title,
        semantic_type,
        "file",
        sources,
        [title],
        evidence,
        evidence[0].confidence if evidence else 0.4,
        order=order,
        output_path=f"content/{filename}",
    )


def _nav_infos(publication: NormalizedPublication, source: str | None = None) -> list[_NavInfo]:
    result = []
    trees = [("nav", publication.nav_toc), ("ncx", publication.ncx_toc)]
    for kind, tree in trees:
        if source and source != kind:
            continue
        for node in flatten_nav(tree):
            if node.href:
                path, fragment = split_fragment(node.href)
                result.append(_NavInfo(node.title, node.href, fragment, node.semantic_type, kind))
    return result


def _resource_for_entry(publication: NormalizedPublication, entry: SpineEntry) -> Resource | None:
    return publication.resources.get(entry.idref)


def _convertible(resource: Resource | None) -> bool:
    return resource is not None and (
        resource.media_type in CONTENT_TYPES or resource.href.endswith((".xhtml", ".html", ".htm", ".xml"))
    )


def _parse(resource: Resource) -> etree._Element:
    return parse_document(resource.content or b"")


def _heading_data(root: etree._Element) -> dict[str, str]:
    result = {}
    for node in root.iter():
        node_id = node.get("id")
        if local_name(getattr(node, "tag", "")) in {"h1", "h2"} and node_id:
            result[node_id] = child_text(node)
    return result


def _heading_texts(content: bytes | None) -> list[str]:
    if not content:
        return []
    try:
        root = parse_document(content)
    except Exception:
        return []
    return [child_text(n) for n in root.iter() if local_name(getattr(n, "tag", "")) in {"h1", "h2"} and child_text(n)]


def _heading_fallback(content: bytes | None) -> str | None:
    values = _heading_texts(content)
    return values[0] if values else None
