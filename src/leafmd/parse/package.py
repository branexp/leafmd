"""container.xml + OPF metadata / manifest / spine."""

from __future__ import annotations

from zipfile import ZipFile

from leafmd.errors import FatalConversionError
from leafmd.model.issues import IssueSeverity
from leafmd.model.publication import BookMetadata, Resource, SpineEntry
from leafmd.model.report import ConversionReport
from leafmd.parse.hrefs import posix_join, posix_norm
from leafmd.parse.xmlutil import attr, child_text, local_name, parse_xml


def read_package_path(archive: ZipFile) -> str:
    try:
        data = archive.read("META-INF/container.xml")
    except KeyError as exc:
        raise FatalConversionError(
            "PARSE_NO_CONTAINER",
            "Missing META-INF/container.xml",
        ) from exc
    root = parse_xml(data)
    for node in root.iter():
        if local_name(node.tag) == "rootfile":
            full_path = attr(node, "full-path")
            if full_path:
                return posix_norm(full_path)
    raise FatalConversionError("PARSE_NO_ROOTFILE", "container.xml has no rootfile")


def parse_package(
    archive: ZipFile,
    package_path: str,
    report: ConversionReport,
) -> tuple[str, BookMetadata, dict[str, Resource], list[SpineEntry], str | None, list[tuple[str, str, str]]]:
    try:
        data = archive.read(package_path)
    except KeyError as exc:
        raise FatalConversionError("PARSE_NO_PACKAGE", f"Missing package document: {package_path}") from exc

    root = parse_xml(data)
    version = attr(root, "version") or "2.0"
    metadata = BookMetadata(title="Untitled")
    resources: dict[str, Resource] = {}
    spine: list[SpineEntry] = []
    cover_id: str | None = None
    guide: list[tuple[str, str, str]] = []

    for node in root.iter():
        name = local_name(node.tag)
        if name == "title" and not metadata.title or name == "title" and metadata.title == "Untitled":
            text = child_text(node)
            if text:
                metadata = _replace(metadata, title=text)
        elif name == "language" and metadata.language is None:
            text = child_text(node)
            if text:
                metadata = _replace(metadata, language=text)
        elif name == "creator":
            text = child_text(node)
            if text:
                metadata = _replace(metadata, authors=(*metadata.authors, text))
        elif name == "publisher" and metadata.publisher is None:
            text = child_text(node)
            if text:
                metadata = _replace(metadata, publisher=text)
        elif name == "date" and metadata.date is None:
            text = child_text(node)
            if text:
                metadata = _replace(metadata, date=text)
        elif name == "rights" and metadata.rights is None:
            text = child_text(node)
            if text:
                metadata = _replace(metadata, rights=text)
        elif name == "description" and metadata.description is None:
            text = child_text(node)
            if text:
                metadata = _replace(metadata, description=text)
        elif name == "identifier":
            text = child_text(node)
            if text:
                metadata = _replace(metadata, identifiers=(*metadata.identifiers, text))
        elif name == "meta":
            meta_name = attr(node, "name")
            meta_content = attr(node, "content")
            if meta_name == "cover" and meta_content:
                cover_id = meta_content
            prop = attr(node, "property")
            if prop == "dcterms:modified" and metadata.date is None:
                text = child_text(node)
                if text:
                    metadata = _replace(metadata, date=text)
        elif name == "item":
            item_id = attr(node, "id")
            href = attr(node, "href")
            media_type = attr(node, "media-type") or "application/octet-stream"
            if not item_id or not href:
                report.add(
                    IssueSeverity.WARNING,
                    "PARSE_ITEM_INCOMPLETE",
                    "Manifest item missing id or href",
                    where=package_path,
                )
                continue
            properties = frozenset((attr(node, "properties") or "").split())
            abs_href = posix_join(package_path, href)
            content: bytes | None
            try:
                content = archive.read(abs_href)
            except KeyError:
                content = None
                report.add(
                    IssueSeverity.WARNING,
                    "PARSE_MISSING_ITEM",
                    f"Manifest item not in archive: {abs_href}",
                    where=item_id,
                )
            resources[item_id] = Resource(
                id=item_id,
                href=abs_href,
                media_type=media_type,
                properties=properties,
                content=content,
            )
            if "cover-image" in properties:
                cover_id = item_id
        elif name == "itemref":
            idref = attr(node, "idref")
            if not idref:
                continue
            resource = resources.get(idref)
            href = resource.href if resource else idref
            linear = (attr(node, "linear") or "yes") != "no"
            spine.append(SpineEntry(idref=idref, linear=linear, href=href))
        elif name == "reference":
            title = attr(node, "title") or ""
            href = attr(node, "href") or ""
            ref_type = attr(node, "type") or ""
            if href:
                guide.append((title, posix_join(package_path, href), ref_type))

    if not spine:
        raise FatalConversionError("PARSE_EMPTY_SPINE", "Package document has an empty spine")

    return version, metadata, resources, spine, cover_id, guide


def _replace(metadata: BookMetadata, **changes: object) -> BookMetadata:
    data: dict[str, tuple[str, ...] | str | None] = {
        "title": metadata.title,
        "language": metadata.language,
        "authors": metadata.authors,
        "subtitle": metadata.subtitle,
        "identifiers": metadata.identifiers,
        "publisher": metadata.publisher,
        "date": metadata.date,
        "rights": metadata.rights,
        "description": metadata.description,
    }
    for key, value in changes.items():
        if key in data:
            data[key] = value  # type: ignore[assignment]
    return BookMetadata(
        title=str(data["title"] or "Untitled"),
        language=data["language"] if isinstance(data["language"], str) else None,
        authors=data["authors"] if isinstance(data["authors"], tuple) else (),
        subtitle=data["subtitle"] if isinstance(data["subtitle"], str) else None,
        identifiers=data["identifiers"] if isinstance(data["identifiers"], tuple) else (),
        publisher=data["publisher"] if isinstance(data["publisher"], str) else None,
        date=data["date"] if isinstance(data["date"], str) else None,
        rights=data["rights"] if isinstance(data["rights"], str) else None,
        description=data["description"] if isinstance(data["description"], str) else None,
    )
