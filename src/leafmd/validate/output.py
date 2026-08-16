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
    if not book:
        report.finalize()
        return report

    sections = book.get("sections") or []
    seen_ids: set[str] = set()
    seen_anchors: set[str] = set()
    for section in sections:
        path = section.get("path")
        section_id = section.get("id")
        if section_id in seen_ids:
            report.add(IssueSeverity.ERROR, "VALIDATE_DUP_SECTION", f"Duplicate section id {section_id}")
        if section_id:
            seen_ids.add(section_id)
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
        if href.startswith("#"):
            target = section_path
            fragment = href[1:] or None
        elif "#" in href:
            target, fragment = href.split("#", 1)
            fragment = fragment or None
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
        if fragment:
            dest_text = resolved.read_text(encoding="utf-8")
            if f'id="{fragment}"' not in dest_text and f"id='{fragment}'" not in dest_text:
                # Heading slugs are not the contract; explicit anchors are.
                if f'id="{fragment}"' not in dest_text:
                    report.add(
                        IssueSeverity.WARNING,
                        "VALIDATE_ANCHOR_MISSING",
                        f"Missing explicit anchor {fragment} in {resolved.name}",
                        where=section_path,
                    )


def _walk_toc(book_dir: Path, nodes: list[Any], report: ConversionReport) -> None:
    for node in nodes:
        href = node.get("href")
        if href:
            target = href.split("#", 1)[0]
            if target and not (book_dir / target).is_file():
                report.add(
                    IssueSeverity.WARNING,
                    "VALIDATE_TOC_MISSING",
                    f"TOC href missing: {href}",
                    where=href,
                )
        _walk_toc(book_dir, node.get("children") or [], report)


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
