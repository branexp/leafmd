"""Open EPUB ZIPs and apply the remaining package-level policy checks."""

from __future__ import annotations

import zipfile
from pathlib import Path

from leafmd.errors import FatalConversionError
from leafmd.model.issues import IssueSeverity
from leafmd.model.report import ConversionReport


def inspect_epub_archive(path: Path, report: ConversionReport) -> zipfile.ZipFile:
    """Open an EPUB after ZIP validity and DRM checks.

    Members are read directly from the archive; leafmd does not extract them to
    the filesystem. Archive member names and sizes are therefore not treated
    as output paths or as a resource-budget policy here. The returned ZipFile
    is still positioned for later readers. Callers own closing it.
    """
    if not path.is_file():
        raise FatalConversionError("INGEST_MISSING", f"EPUB not found: {path}")

    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise FatalConversionError("INGEST_NOT_ZIP", f"Not a ZIP/EPUB archive: {path}") from exc

    names = archive.namelist()
    has_encryption = False
    for info in archive.infolist():
        name = info.filename
        if name.replace("\\", "/").rstrip("/") == "META-INF/encryption.xml":
            has_encryption = True

    if has_encryption:
        archive.close()
        raise FatalConversionError(
            "INGEST_DRM",
            "Encrypted/DRM EPUB rejected (META-INF/encryption.xml present)",
        )

    if "mimetype" not in names:
        report.add(
            IssueSeverity.WARNING,
            "INGEST_NO_MIMETYPE",
            "Archive is missing the EPUB mimetype member",
            where=str(path),
        )
    else:
        try:
            declared = archive.read("mimetype").decode("ascii", errors="replace").strip()
        except Exception:
            declared = ""
        if declared and declared != "application/epub+zip":
            report.add(
                IssueSeverity.WARNING,
                "INGEST_MIMETYPE",
                f"Unexpected mimetype: {declared}",
                where="mimetype",
            )

    return archive
