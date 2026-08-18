"""Select copied raster assets for optional semantic image analysis."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from leafmd.images import ImageAnalyzer
from leafmd.model.images import ImageAnalysis, ImageDecision
from leafmd.model.issues import IssueSeverity
from leafmd.model.publication import NormalizedPublication
from leafmd.model.report import ConversionReport

_ELIGIBLE_MEDIA_TYPES = frozenset({"image/jpeg", "image/jpg", "image/png", "image/webp"})
_ELIGIBLE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})


def analyze_publication_images(
    publication: NormalizedPublication,
    asset_map: dict[str, str],
    book_dir: Path,
    analyzer: ImageAnalyzer,
    report: ConversionReport,
) -> dict[str, ImageAnalysis]:
    """Analyze eligible copied raster assets once per source EPUB resource."""

    resources = {resource.href: resource for resource in publication.resources.values()}
    cover_href = None
    if publication.cover_id and publication.cover_id in publication.resources:
        cover_href = publication.resources[publication.cover_id].href

    selected: dict[str, Path] = {}
    for source_href, mapped in sorted(asset_map.items()):
        if source_href == cover_href:
            continue
        resource = resources.get(source_href)
        if resource is None or not _eligible(resource.media_type, source_href):
            continue
        relative = mapped[3:] if mapped.startswith("../") else mapped
        candidate = (book_dir / relative).resolve()
        try:
            candidate.relative_to(book_dir.resolve())
        except ValueError:
            continue
        if candidate.is_file():
            selected[source_href] = candidate

    if not selected:
        return {}
    report.stats.images_analyzed += len(selected)
    try:
        results = analyzer.analyze_batch(selected)
        if not isinstance(results, Mapping):
            raise TypeError("analyzer returned a non-mapping result")
    except Exception as exc:  # optional enhancement must never prevent EPUB conversion
        report.stats.image_analysis_failures += len(selected)
        report.add(
            IssueSeverity.WARNING,
            "IMAGE_ANALYSIS_FAILED",
            f"{analyzer.backend} failed; preserved original raster images: {exc}",
        )
        return {}

    normalized: dict[str, ImageAnalysis] = {}
    for source_href in selected:
        analysis = results.get(source_href)
        if analysis is None:
            report.stats.image_analysis_failures += 1
            report.add(
                IssueSeverity.WARNING,
                "IMAGE_ANALYSIS_MISSING",
                f"{analyzer.backend} returned no result; preserved image",
                where=source_href,
            )
            continue
        normalized[source_href] = analysis
        if analysis.decision is ImageDecision.REPLACE:
            report.add(
                IssueSeverity.INFO,
                "IMAGE_ANALYSIS_CANDIDATE",
                f"Image is Markdown-representable via {analysis.backend}: {', '.join(analysis.labels) or 'content'}",
                where=source_href,
            )
        else:
            report.add(
                IssueSeverity.INFO,
                "IMAGE_PRESERVED",
                f"Preserved image after {analysis.backend} analysis ({analysis.reason})",
                where=source_href,
            )
    return normalized


def _eligible(media_type: str, href: str) -> bool:
    return media_type.lower() in _ELIGIBLE_MEDIA_TYPES or Path(href).suffix.lower() in _ELIGIBLE_SUFFIXES
