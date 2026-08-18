"""Top-level convert pipeline."""

from __future__ import annotations

from pathlib import Path

from leafmd.errors import FatalConversionError
from leafmd.images import ImageAnalyzer
from leafmd.ingest.archive import inspect_epub_archive
from leafmd.model.issues import IssueSeverity
from leafmd.model.report import ConversionReport
from leafmd.parse.ebooklib_adapter import load_publication
from leafmd.render.writer import write_book_directory, write_report
from leafmd.report import new_report
from leafmd.semantics.plan import plan_sections
from leafmd.transform.slug import slugify


def convert_epub(
    epub_path: Path,
    output_dir: Path | None = None,
    *,
    strict: bool = False,
    image_analyzer: ImageAnalyzer | None = None,
) -> tuple[Path, ConversionReport]:
    report = new_report()
    archive = inspect_epub_archive(epub_path, report)
    try:
        publication = load_publication(epub_path, archive, report)
    finally:
        archive.close()

    plans = plan_sections(publication, report)
    if report.has_fatal() or not plans:
        raise FatalConversionError("PLAN_NO_SECTIONS", "No convertible content documents in the spine")

    book_dir = output_dir or Path(slugify(publication.metadata.title, fallback="book"))
    write_book_directory(publication, plans, book_dir, report, image_analyzer=image_analyzer)
    if strict:
        _promote_strict(report)
    write_report(book_dir, report)
    return book_dir, report


def _promote_strict(report: ConversionReport) -> None:
    promote = {"LINK_UNRESOLVED", "ASSET_MISSING", "RENDER_MISSING_SOURCE"}
    for issue in report.issues:
        if issue.severity is IssueSeverity.WARNING and issue.code in promote:
            object.__setattr__(issue, "severity", IssueSeverity.ERROR)
