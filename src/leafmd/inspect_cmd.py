"""Inspect an EPUB without writing a book directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from leafmd.ingest.archive import inspect_epub_archive
from leafmd.parse.ebooklib_adapter import load_publication
from leafmd.parse.navigation import flatten_nav
from leafmd.report import new_report


def inspect_epub(epub_path: Path) -> dict[str, Any]:
    report = new_report()
    archive = inspect_epub_archive(epub_path, report)
    try:
        publication = load_publication(epub_path, archive, report)
    finally:
        archive.close()
    report.finalize()
    return {
        "source_filename": publication.source_filename,
        "epub_version": publication.epub_version,
        "package_path": publication.package_path,
        "title": publication.metadata.title,
        "authors": list(publication.metadata.authors),
        "language": publication.metadata.language,
        "spine": [{"idref": entry.idref, "href": entry.href, "linear": entry.linear} for entry in publication.spine],
        "nav_toc": [{"title": node.title, "href": node.href} for node in flatten_nav(publication.nav_toc)],
        "ncx_toc": [{"title": node.title, "href": node.href} for node in flatten_nav(publication.ncx_toc)],
        "landmarks": [
            {"title": node.title, "href": node.href, "type": node.semantic_type} for node in publication.landmarks
        ],
        "resources": len(publication.resources),
        "issues": [issue.to_dict() for issue in report.issues],
        "status": report.status,
    }
