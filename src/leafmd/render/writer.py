"""Write a canonical book directory from a planned publication."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from leafmd import __version__
from leafmd.model.publication import NormalizedPublication
from leafmd.model.report import ConversionReport
from leafmd.model.section import SectionPlan
from leafmd.parse.hrefs import split_fragment
from leafmd.parse.html import parse_document
from leafmd.render.markdown import render_section
from leafmd.transform.assets import collect_and_copy_assets
from leafmd.transform.links import TargetMap, build_target_map, rewrite_tree
from leafmd.transform.merge import merge_documents
from leafmd.transform.slice import slice_document
from leafmd.transform.textnorm import description_to_markdown


def write_book_directory(
    publication: NormalizedPublication,
    plans: list[SectionPlan],
    output_dir: Path,
    report: ConversionReport,
) -> Path:
    book_dir = output_dir
    book_dir.mkdir(parents=True, exist_ok=True)
    (book_dir / "content").mkdir(exist_ok=True)

    asset_map = collect_and_copy_assets(publication, plans, book_dir, report)
    targets = build_target_map(publication, plans, report)

    generated = 0
    for plan in plans:
        if plan.role != "file" or not plan.output_path:
            continue
        roots = []
        missing_path = plan.sources[0].href if plan.sources else plan.id
        for source in plan.sources:
            path, _fragment = split_fragment(source.href)
            resource = next((item for item in publication.resources.values() if item.href == path), None)
            if resource is None or resource.content is None:
                continue
            root = parse_document(resource.content)
            if source.start_id or source.end_id:
                root = slice_document(root, source.start_id, source.end_id)
            rewrite_tree(root, path, targets, asset_map, report, plan.output_path)
            roots.append(root)
        if not roots:
            from leafmd.model.issues import IssueSeverity

            report.add(
                IssueSeverity.ERROR,
                "RENDER_MISSING_SOURCE",
                f"No bytes for section source {missing_path}",
                where=plan.id,
            )
            continue
        root = merge_documents(roots)
        markdown = render_section(root, plan, targets.by_href)
        dest = book_dir / plan.output_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(markdown, encoding="utf-8")
        generated += 1

    report.stats.source_documents = sum(
        1
        for entry in publication.spine
        if publication.resources.get(entry.idref) is not None
        and (
            publication.resources[entry.idref].media_type
            in {"application/xhtml+xml", "text/html", "application/xml", "text/xml"}
            or publication.resources[entry.idref].href.endswith((".xhtml", ".html", ".htm"))
        )
    )
    report.stats.generated_files = generated

    _write_json(book_dir / "book.json", _book_json(publication, plans, asset_map))
    _write_json(book_dir / "toc.json", _toc_json(publication, plans, targets))
    (book_dir / "index.md").write_text(_index_markdown(publication, plans, asset_map), encoding="utf-8")
    (book_dir / "toc.md").write_text(_toc_markdown(publication, plans, targets), encoding="utf-8")
    return book_dir


def write_report(book_dir: Path, report: ConversionReport) -> None:
    report.finalize()
    _write_json(book_dir / "conversion-report.json", report.to_dict())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _book_json(
    publication: NormalizedPublication,
    plans: list[SectionPlan],
    asset_map: dict[str, str],
) -> dict[str, Any]:
    cover = None
    if publication.cover_id and publication.cover_id in publication.resources:
        cover_res = publication.resources[publication.cover_id]
        mapped = asset_map.get(cover_res.href)
        cover = {
            "path": mapped[3:] if mapped and mapped.startswith("../") else mapped,
            "source_href": cover_res.href,
            "media_type": cover_res.media_type,
        }
    return {
        "schema_version": 1,
        "title": publication.metadata.title,
        "subtitle": publication.metadata.subtitle,
        "authors": list(publication.metadata.authors),
        "language": publication.metadata.language,
        "identifiers": list(publication.metadata.identifiers),
        "publisher": publication.metadata.publisher,
        "date": publication.metadata.date,
        "rights": publication.metadata.rights,
        "description": publication.metadata.description,
        "epub_version": publication.epub_version,
        "source_filename": publication.source_filename,
        "package_path": publication.package_path,
        "cover": cover,
        "sections": [
            {
                "id": plan.id,
                "order": plan.order,
                "type": plan.type,
                "title": plan.title,
                "path": plan.output_path,
                "role": plan.role,
                "toc_path": plan.toc_path,
                "sources": [{"href": source.href, "fragment": source.start_id} for source in plan.sources],
                "confidence": plan.confidence,
            }
            for plan in plans
        ],
        "assets": [
            {
                "source_href": href,
                "path": rel[3:] if rel.startswith("../") else rel,
                "media_type": next(
                    (item.media_type for item in publication.resources.values() if item.href == href),
                    None,
                ),
            }
            for href, rel in sorted(asset_map.items())
        ],
        "conversion": {
            "tool": "leafmd",
            "tool_version": __version__,
        },
    }


def _toc_href(href: str | None, targets: TargetMap) -> str | None:
    if not href:
        return None
    target = targets.resolve_abs(href)
    if target is None:
        return None
    return f"{target.path}#{target.anchor}" if target.anchor else target.path


def _toc_json(
    publication: NormalizedPublication,
    plans: list[SectionPlan],
    targets: TargetMap,
) -> dict[str, Any]:
    by_href = {split_fragment(plan.sources[0].href)[0]: plan for plan in plans if plan.sources}

    def convert(nodes: list[Any], provenance: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for node in nodes:
            path, _fragment = split_fragment(node.href) if node.href else (None, None)
            plan = by_href.get(path) if path else None
            href = _toc_href(node.href, targets)
            if href is None and plan and plan.output_path:
                href = plan.output_path
            out.append(
                {
                    "title": node.title,
                    "type": node.semantic_type or (plan.type if plan else None),
                    "section_id": plan.id if plan else None,
                    "href": href,
                    "provenance": provenance,
                    "children": convert(list(node.children), provenance),
                }
            )
        return out

    combined = _union_toc(publication.nav_toc, publication.ncx_toc)
    tree = convert(combined, "nav+ncx")
    if not tree:
        tree = convert(publication.ncx_toc, "ncx")
    if not tree:
        tree = [
            {
                "title": plan.title,
                "type": plan.type,
                "section_id": plan.id,
                "href": plan.output_path,
                "provenance": "inferred",
                "children": [],
            }
            for plan in plans
        ]
    return {"schema_version": 1, "nodes": tree}


def _index_markdown(
    publication: NormalizedPublication,
    plans: list[SectionPlan],
    asset_map: dict[str, str],
) -> str:
    authors = ", ".join(publication.metadata.authors)
    first = next((plan for plan in plans if plan.output_path), None)
    cover_line = ""
    if publication.cover_id and publication.cover_id in publication.resources:
        mapped = asset_map.get(publication.resources[publication.cover_id].href)
        if mapped:
            cover_path = mapped[3:] if mapped.startswith("../") else mapped
            cover_line = f"\n![Cover]({cover_path})\n"
    description = description_to_markdown(publication.metadata.description)
    first_link = f"[{first.title}]({first.output_path})" if first and first.output_path else ""
    return (
        f"# {publication.metadata.title}\n\n"
        + (f"{authors}\n\n" if authors else "")
        + (f"{description}\n\n" if description else "")
        + cover_line
        + (f"Start: {first_link}\n\n" if first_link else "")
        + "See [toc.md](toc.md) for the full contents.\n"
    )


def _toc_markdown(publication: NormalizedPublication, plans: list[SectionPlan], targets: TargetMap) -> str:
    nodes = _union_toc(publication.nav_toc, publication.ncx_toc)
    if nodes:
        lines = ["# Contents", ""]
        lines.extend(_render_toc_nodes(nodes, plans, targets, depth=0))
        return "\n".join(lines) + "\n"
    lines = ["# Contents", ""]
    for plan in plans:
        if plan.output_path:
            lines.append(f"- [{plan.title}]({plan.output_path})")
    return "\n".join(lines) + "\n"


def _union_toc(primary: list[Any], secondary: list[Any]) -> list[Any]:
    """Union navigation trees, retaining nav labels and order on collisions."""
    if not primary:
        return list(secondary)
    result = list(primary)
    keys = {_toc_key(node) for node in result}
    for node in secondary:
        key = _toc_key(node)
        if key in keys:
            existing = next(item for item in result if _toc_key(item) == key)
            children = _union_toc(list(existing.children), list(node.children))
            if children != list(existing.children):
                from leafmd.model.publication import NavNode

                result[result.index(existing)] = NavNode(
                    existing.title,
                    existing.href,
                    existing.kind,
                    existing.semantic_type,
                    tuple(children),
                )
        else:
            result.append(node)
            keys.add(key)
    return result


def _toc_key(node: Any) -> tuple[str, str | None]:
    if not node.href:
        return (node.title, None)
    return split_fragment(node.href)


def _render_toc_nodes(
    nodes: list[Any],
    plans: list[SectionPlan],
    targets: TargetMap,
    depth: int,
) -> list[str]:
    by_href = {split_fragment(plan.sources[0].href)[0]: plan for plan in plans if plan.sources}
    lines: list[str] = []
    indent = "  " * depth
    for node in nodes:
        path = split_fragment(node.href)[0] if node.href else None
        plan = by_href.get(path) if path else None
        label = node.title
        href = _toc_href(node.href, targets)
        if href is None and plan and plan.output_path:
            href = plan.output_path
        if href:
            lines.append(f"{indent}- [{label}]({href})")
        else:
            lines.append(f"{indent}- {label}")
        if node.children:
            lines.extend(_render_toc_nodes(list(node.children), plans, targets, depth + 1))
    return lines
