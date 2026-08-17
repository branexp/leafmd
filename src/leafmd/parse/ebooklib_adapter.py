"""EbookLib is the ZIP/item reader. Navigation truth is parsed here, not via book.toc."""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile

from leafmd.errors import FatalConversionError
from leafmd.model.issues import IssueSeverity
from leafmd.model.publication import NormalizedPublication, Resource
from leafmd.model.report import ConversionReport
from leafmd.parse.navigation import guide_to_nodes, parse_html_toc, parse_nav_document, parse_ncx
from leafmd.parse.package import parse_package, read_package_path

# EbookLib is imported only in this module.
try:
    from ebooklib import epub as _epub
except ImportError:  # pragma: no cover - dependency is required at runtime
    _epub = None


def load_publication(path: Path, archive: ZipFile, report: ConversionReport) -> NormalizedPublication:
    package_path = read_package_path(archive)
    version, metadata, resources, spine, cover_id, guide = parse_package(archive, package_path, report)
    _maybe_crosscheck_ebooklib(path, report)

    nav_resource = _first_with_property(resources, "nav")
    ncx_resource = _first_media(resources, "application/x-dtbncx+xml")
    nav_toc, landmarks = parse_nav_document(nav_resource, report) if nav_resource else ([], [])
    if nav_resource is None and version.startswith("3"):
        report.add(
            IssueSeverity.WARNING,
            "NAV_MISSING",
            "EPUB 3 package has no nav document; falling back to NCX/spine",
            where=package_path,
        )
    ncx_toc = parse_ncx(ncx_resource, report) if ncx_resource else []
    if not nav_toc:
        for candidate in _html_toc_candidates(resources):
            recovered = parse_html_toc(candidate)
            if recovered:
                nav_toc = recovered
                break
    if not nav_toc and not ncx_toc:
        report.add(
            IssueSeverity.WARNING,
            "NAV_DEGRADED",
            "No usable nav or NCX; section titles will come from spine/headings",
            where=package_path,
        )

    return NormalizedPublication(
        schema_version=1,
        metadata=metadata,
        epub_version=version,
        package_path=package_path,
        source_filename=path.name,
        resources=resources,
        spine=spine,
        nav_toc=nav_toc,
        ncx_toc=ncx_toc,
        landmarks=landmarks,
        guide=guide_to_nodes(guide),
        cover_id=cover_id,
    )


def _maybe_crosscheck_ebooklib(path: Path, report: ConversionReport) -> None:
    if _epub is None:
        report.add(
            IssueSeverity.WARNING,
            "EBOOKLIB_MISSING",
            "EbookLib is not installed; using direct ZIP/OPF parse only",
        )
        return
    try:
        book = _epub.read_epub(str(path), options={"ignore_ncx": True})
    except Exception as exc:  # noqa: BLE001 - adapter must not crash the convert
        report.add(
            IssueSeverity.WARNING,
            "EBOOKLIB_READ",
            f"EbookLib could not read the book ({exc}); continuing with direct parse",
            where=str(path),
        )
        return
    if not getattr(book, "spine", None):
        raise FatalConversionError("EBOOKLIB_EMPTY", "EbookLib reported an empty spine")


def _first_with_property(resources: dict[str, Resource], prop: str) -> Resource | None:
    for resource in resources.values():
        if prop in resource.properties:
            return resource
    return None


def _first_media(resources: dict[str, Resource], media_type: str) -> Resource | None:
    for resource in resources.values():
        if resource.media_type == media_type:
            return resource
    return None


def _html_toc_candidates(resources: dict[str, Resource]) -> list[Resource]:
    """Prefer a spine HTML file named like a TOC when EPUB 3 nav is absent."""
    ranked: list[tuple[int, Resource]] = []
    for resource in resources.values():
        name = f"{resource.id} {resource.href}".lower()
        score = 0
        if re.search(r"(?:^|[._\-\s/])toc(?:[._\-\s]|$)", name):
            score += 2
        if "contents" in name:
            score += 1
        if score:
            ranked.append((score, resource))
    ranked.sort(key=lambda item: (-item[0], item[1].href))
    return [item[1] for item in ranked]
