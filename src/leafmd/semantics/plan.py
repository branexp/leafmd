"""Phase 1 planner: one linear spine XHTML document → one file."""

from __future__ import annotations

from leafmd.model.issues import IssueSeverity
from leafmd.model.publication import NormalizedPublication
from leafmd.model.report import ConversionReport
from leafmd.model.section import SectionPlan, SourceRange
from leafmd.parse.hrefs import split_fragment
from leafmd.parse.navigation import flatten_nav
from leafmd.semantics.classify import classify_from_title
from leafmd.transform.slug import slugify

CONTENT_TYPES = {
    "application/xhtml+xml",
    "text/html",
    "application/xml",
    "text/xml",
}


def plan_sections(publication: NormalizedPublication, report: ConversionReport) -> list[SectionPlan]:
    href_titles = _href_title_map(publication)
    plans: list[SectionPlan] = []
    order = 0
    for entry in publication.spine:
        resource = publication.resources.get(entry.idref)
        if resource is None:
            report.add(
                IssueSeverity.ERROR,
                "PLAN_MISSING_SPINE_ITEM",
                f"Spine idref not in manifest: {entry.idref}",
                where=entry.idref,
            )
            continue
        if resource.media_type not in CONTENT_TYPES and not resource.href.endswith((".xhtml", ".html", ".htm", ".xml")):
            continue
        if not entry.linear:
            report.add(
                IssueSeverity.INFO,
                "PLAN_NONLINEAR",
                "Included non-linear spine item as its own file",
                where=resource.href,
            )
        order += 1
        path, _fragment = split_fragment(resource.href)
        title = href_titles.get(path) or _heading_fallback(resource.content) or resource.id
        semantic_type, evidence = classify_from_title(title, resource)
        section_id = f"sec-{order:03d}"
        filename = f"{order:03d}-{semantic_type}-{slugify(title)}.md"
        plans.append(
            SectionPlan(
                id=section_id,
                title=title,
                type=semantic_type,
                role="file",
                sources=[SourceRange(href=resource.href)],
                toc_path=[title],
                evidence=evidence,
                confidence=evidence[0].confidence if evidence else 0.4,
                parent_id=None,
                order=order,
                output_path=f"content/{filename}",
            )
        )
    if not plans:
        report.add(
            IssueSeverity.FATAL,
            "PLAN_NO_SECTIONS",
            "No convertible content documents in the spine",
        )
    return plans


def _href_title_map(publication: NormalizedPublication) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for node in flatten_nav(publication.nav_toc) + flatten_nav(publication.ncx_toc):
        if not node.href:
            continue
        path, _fragment = split_fragment(node.href)
        mapping.setdefault(path, node.title)
    return mapping


def _heading_fallback(content: bytes | None) -> str | None:
    if not content:
        return None
    from leafmd.parse.html import parse_document
    from leafmd.parse.xmlutil import child_text, local_name

    try:
        root = parse_document(content)
    except Exception:  # noqa: BLE001
        return None
    for node in root.iter():
        if local_name(getattr(node, "tag", "")) in {"h1", "h2", "title"}:
            text = child_text(node)
            if text:
                return text
    return None
