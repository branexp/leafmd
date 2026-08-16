"""Re-check a generated book directory."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from leafmd.model.issues import ConversionIssue, IssueSeverity
from leafmd.model.report import ConversionReport
from leafmd.report import new_report

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
HTML_HREF = re.compile(r"""(?:href|src)=["']([^"']+)["']""")
HTML_ID = re.compile(r"""id=["']([^"']+)["']""")
FRONTMATTER_ID = re.compile(r"^id:\s*(\S+)", re.M)


def validate_book_directory(book_dir: Path) -> ConversionReport:
    report = new_report()
    required = ["book.json", "toc.json", "conversion-report.json", "index.md", "toc.md"]
    for name in required:
        if not (book_dir / name).is_file():
            report.add(IssueSeverity.ERROR, "VALIDATE_MISSING_FILE", f"Missing {name}", where=name)

    book = _load_json(book_dir / "book.json", report, "book.json")
    toc = _load_json(book_dir / "toc.json", report, "toc.json")
    conversion = _load_json(book_dir / "conversion-report.json", report, "conversion-report.json")
    if conversion is not None:
        _require_keys(
            conversion,
            {"status", "tool_version", "source_validation", "issues", "stats"},
            report,
            "conversion-report.json",
        )
        stats = conversion.get("stats")
        if isinstance(stats, dict):
            _require_keys(
                stats,
                {"source_documents", "generated_files", "images_copied", "unresolved_links", "assets_skipped"},
                report,
                "conversion-report.json#stats",
            )
    if toc is not None:
        _require_keys(toc, {"schema_version", "nodes"}, report, "toc.json")
    if book is None:
        report.finalize()
        return report

    _require_keys(
        book,
        {"schema_version", "title", "sections", "assets", "conversion"},
        report,
        "book.json",
    )
    conversion_meta = book.get("conversion")
    if isinstance(conversion_meta, dict):
        _require_keys(conversion_meta, {"tool", "tool_version"}, report, "book.json#conversion")

    sections = book.get("sections") or []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    seen_anchors: set[str] = set()
    for section in sections:
        if not isinstance(section, dict):
            report.add(IssueSeverity.ERROR, "VALIDATE_SCHEMA", "Section entry must be an object", where="book.json")
            continue
        _require_keys(
            section,
            {"id", "order", "type", "title", "path", "role", "sources"},
            report,
            f"book.json#sections/{section.get('id') or '?'}",
        )
        path = section.get("path")
        section_id = section.get("id")
        if section_id in seen_ids:
            report.add(IssueSeverity.ERROR, "VALIDATE_DUP_SECTION", f"Duplicate section id {section_id}")
        if section_id:
            seen_ids.add(section_id)
        if isinstance(path, str) and path:
            if path in seen_paths:
                report.add(
                    IssueSeverity.ERROR,
                    "VALIDATE_DUP_PATH",
                    f"Duplicate section path {path}",
                    where=path,
                )
            seen_paths.add(path)
        if not path:
            continue
        full = book_dir / path
        if not full.is_file():
            report.add(IssueSeverity.ERROR, "VALIDATE_MISSING_SECTION", f"Missing {path}", where=path)
            continue
        text = full.read_text(encoding="utf-8")
        fm_id = FRONTMATTER_ID.search(text)
        if section_id and fm_id and fm_id.group(1) != section_id:
            report.add(
                IssueSeverity.WARNING,
                "VALIDATE_ID_MISMATCH",
                f"Frontmatter id {fm_id.group(1)} != {section_id}",
                where=path,
            )
        for match in HTML_ID.finditer(text):
            anchor = match.group(1)
            key = f"{path}#{anchor}"
            if key in seen_anchors:
                report.add(IssueSeverity.ERROR, "VALIDATE_DUP_ANCHOR", f"Duplicate anchor {key}", where=path)
            seen_anchors.add(key)
        _check_links(book_dir, path, text, report)

    if toc:
        _walk_toc(book_dir, toc.get("nodes") or [], report)

    for asset in book.get("assets") or []:
        if not isinstance(asset, dict):
            report.add(IssueSeverity.ERROR, "VALIDATE_SCHEMA", "Asset entry must be an object", where="book.json")
            continue
        asset_path = asset.get("path")
        if asset_path and not (book_dir / asset_path).is_file():
            report.add(
                IssueSeverity.ERROR,
                "VALIDATE_MISSING_ASSET",
                f"Missing asset {asset_path}",
                where=asset_path,
            )

    report.finalize()
    return report


def _check_links(book_dir: Path, section_path: str, text: str, report: ConversionReport) -> None:
    hrefs = [match.group(1) for match in MD_LINK.finditer(text)]
    hrefs.extend(match.group(1) for match in HTML_HREF.finditer(text))
    for href in hrefs:
        if href.startswith(("http://", "https://", "mailto:")):
            continue
        target: str
        fragment: str | None
        if href.startswith("#"):
            target = section_path
            fragment = href[1:] or None
        elif "#" in href:
            href_path, href_fragment = href.split("#", 1)
            target = href_path
            fragment = href_fragment or None
        else:
            target, fragment = href, None
        resolved = (book_dir / section_path).parent / target
        try:
            resolved = resolved.resolve()
            book_root = book_dir.resolve()
            resolved.relative_to(book_root)
        except Exception:
            report.add(
                IssueSeverity.ERROR,
                "VALIDATE_LINK_ESCAPE",
                f"Link escapes book directory: {href}",
                where=section_path,
            )
            continue
        if not resolved.is_file():
            report.add(
                IssueSeverity.WARNING,
                "VALIDATE_LINK_MISSING",
                f"Broken relative link: {href}",
                where=section_path,
            )
            continue
        if fragment and not _has_explicit_anchor(resolved.read_text(encoding="utf-8"), fragment):
            report.add(
                IssueSeverity.WARNING,
                "VALIDATE_ANCHOR_MISSING",
                f"Missing explicit anchor {fragment} in {resolved.name}",
                where=section_path,
            )


def _walk_toc(book_dir: Path, nodes: list[Any], report: ConversionReport) -> None:
    for node in nodes:
        if not isinstance(node, dict):
            report.add(IssueSeverity.ERROR, "VALIDATE_SCHEMA", "TOC node must be an object", where="toc.json")
            continue
        href = node.get("href")
        if href:
            target, fragment = (href.split("#", 1) + [""])[:2]
            full = book_dir / target if target else None
            if full is not None:
                try:
                    full = full.resolve()
                    full.relative_to(book_dir.resolve())
                except Exception:
                    report.add(
                        IssueSeverity.ERROR,
                        "VALIDATE_TOC_ESCAPE",
                        f"TOC href escapes book directory: {href}",
                        where=href,
                    )
                    _walk_toc(book_dir, node.get("children") or [], report)
                    continue
            if target and (full is None or not full.is_file()):
                report.add(
                    IssueSeverity.WARNING,
                    "VALIDATE_TOC_MISSING",
                    f"TOC href missing: {href}",
                    where=href,
                )
            elif fragment and full is not None and not _has_explicit_anchor(full.read_text(encoding="utf-8"), fragment):
                report.add(
                    IssueSeverity.WARNING,
                    "VALIDATE_TOC_ANCHOR_MISSING",
                    f"TOC fragment missing: {href}",
                    where=href,
                )
        _walk_toc(book_dir, node.get("children") or [], report)


def _has_explicit_anchor(text: str, fragment: str) -> bool:
    return f'id="{fragment}"' in text or f"id='{fragment}'" in text


def _require_keys(payload: dict[str, Any], keys: set[str], report: ConversionReport, where: str) -> None:
    missing = sorted(key for key in keys if key not in payload)
    if missing:
        report.add(
            IssueSeverity.ERROR,
            "VALIDATE_SCHEMA",
            f"Missing required field(s): {', '.join(missing)}",
            where=where,
        )


def _load_json(path: Path, report: ConversionReport, label: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.add(IssueSeverity.ERROR, "VALIDATE_JSON", f"Invalid JSON in {label}: {exc}", where=label)
        return None
    if not isinstance(payload, dict):
        report.add(IssueSeverity.ERROR, "VALIDATE_JSON", f"{label} must be an object", where=label)
        return None
    return payload


def issues_as_dicts(issues: list[ConversionIssue]) -> list[dict[str, str | None]]:
    return [issue.to_dict() for issue in issues]
