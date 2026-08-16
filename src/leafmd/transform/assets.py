"""Copy referenced raster/SVG assets. Never fetch remote files."""

from __future__ import annotations

import re
from pathlib import Path

from leafmd.model.issues import IssueSeverity
from leafmd.model.publication import NormalizedPublication, Resource
from leafmd.model.report import ConversionReport
from leafmd.model.section import SectionPlan
from leafmd.parse.hrefs import posix_join, split_fragment
from leafmd.parse.xmlutil import attr, local_name
from leafmd.transform.slug import slugify

IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}
SKIP_TYPES_PREFIX = ("font/", "text/css", "application/javascript", "text/javascript")
SKIP_EXACT = {
    "application/vnd.ms-opentype",
    "application/font-sfnt",
    "audio/mpeg",
    "audio/mp4",
    "video/mp4",
    "application/smil+xml",
}

SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.I | re.S)
FOREIGN_RE = re.compile(r"<foreignObject\b[^>]*>.*?</foreignObject>", re.I | re.S)
EVENT_RE = re.compile(r"\son[a-z]+\s*=\s*('[^']*'|\"[^\"]*\")", re.I)
HANDLER_RE = re.compile(r"\shandler\s*=\s*('[^']*'|\"[^\"]*\")", re.I)
XLINK_RE = re.compile(r"""\s(?:xlink:)?href\s*=\s*['"](?:https?:|javascript:|data:)[^'"]*['"]""", re.I)


def collect_and_copy_assets(
    publication: NormalizedPublication,
    plans: list[SectionPlan],
    book_dir: Path,
    report: ConversionReport,
) -> dict[str, str]:
    needed: dict[str, Resource] = {}
    for plan in plans:
        for source in plan.sources:
            path, _fragment = split_fragment(source.href)
            resource = next((item for item in publication.resources.values() if item.href == path), None)
            if resource is None or resource.content is None:
                continue
            from leafmd.parse.html import parse_document

            try:
                root = parse_document(resource.content)
            except Exception:  # noqa: BLE001
                continue
            for node in root.iter():
                if local_name(getattr(node, "tag", "")) != "img":
                    continue
                src = attr(node, "src")
                if not src or src.startswith(("http://", "https://", "data:")):
                    continue
                joined, _frag = split_fragment(posix_join(resource.href, src))
                match = next((item for item in publication.resources.values() if item.href == joined), None)
                if match is not None:
                    needed[joined] = match

    if publication.cover_id and publication.cover_id in publication.resources:
        cover = publication.resources[publication.cover_id]
        needed[cover.href] = cover

    asset_map: dict[str, str] = {}
    image_dir = book_dir / "assets" / "images"
    for href, resource in sorted(needed.items()):
        if resource.media_type.startswith(SKIP_TYPES_PREFIX) or resource.media_type in SKIP_EXACT:
            report.add(
                IssueSeverity.WARNING,
                "MEDIA_SKIPPED",
                f"Skipped non-image resource: {href}",
                where=href,
            )
            report.stats.assets_skipped += 1
            continue
        if resource.media_type not in IMAGE_TYPES and not href.lower().endswith(
            (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")
        ):
            report.add(
                IssueSeverity.WARNING,
                "MEDIA_SKIPPED",
                f"Skipped unsupported asset type {resource.media_type}: {href}",
                where=href,
            )
            report.stats.assets_skipped += 1
            continue
        if resource.content is None:
            report.add(IssueSeverity.WARNING, "ASSET_MISSING", f"Asset has no bytes: {href}", where=href)
            continue
        image_dir.mkdir(parents=True, exist_ok=True)
        filename = _unique_output_name(href, resource, image_dir)
        dest = image_dir / filename
        payload = resource.content
        if resource.media_type == "image/svg+xml" or href.lower().endswith(".svg"):
            payload = sanitize_svg(payload, report, href)
        dest.write_bytes(payload)
        rel = f"assets/images/{filename}"
        asset_map[href] = f"../{rel}"
        report.stats.images_copied += 1
    return asset_map


def sanitize_svg(data: bytes, report: ConversionReport, where: str) -> bytes:
    text = data.decode("utf-8", errors="replace")
    cleaned = SCRIPT_RE.sub("", text)
    cleaned = FOREIGN_RE.sub("", cleaned)
    cleaned = EVENT_RE.sub("", cleaned)
    cleaned = HANDLER_RE.sub("", cleaned)
    cleaned = XLINK_RE.sub("", cleaned)
    if cleaned != text:
        report.add(
            IssueSeverity.WARNING,
            "SVG_SANITIZED",
            "Stripped script/event/external refs from SVG",
            where=where,
        )
    return cleaned.encode("utf-8")


def _output_name(href: str, resource: Resource) -> str:
    raw = href.rsplit("/", 1)[-1] or resource.id
    stem, dot, suffix = raw.rpartition(".")
    safe_stem = slugify(stem or resource.id, fallback=resource.id)
    safe_suffix = slugify(suffix, fallback="bin") if dot else "bin"
    return f"{safe_stem}.{safe_suffix}"


def _unique_output_name(href: str, resource: Resource, image_dir: Path) -> str:
    filename = _output_name(href, resource)
    stem, dot, suffix = filename.rpartition(".")
    n = 2
    candidate = filename
    while (image_dir / candidate).exists():
        candidate = f"{stem}-{n}.{suffix}" if dot else f"{filename}-{n}"
        n += 1
    return candidate
