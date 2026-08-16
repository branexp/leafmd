"""ZIP / DRM / bomb checks before any XML parse."""

from __future__ import annotations

import zipfile
from pathlib import Path

from leafmd.errors import FatalConversionError
from leafmd.model.issues import IssueSeverity
from leafmd.model.report import ConversionReport

MAX_ENTRIES = 20_000
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_SINGLE_MEMBER_BYTES = 20 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100.0
MIN_COMPRESSED_FOR_RATIO = 1024


def _is_unsafe_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("\\"):
        return True
    if ":" in Path(normalized).parts[0] if Path(normalized).parts else False:
        return True
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    return any(part == ".." for part in parts) or normalized.startswith("../")


def inspect_epub_archive(path: Path, report: ConversionReport) -> zipfile.ZipFile:
    """Open an EPUB after path / bomb / DRM checks.

    The returned ZipFile is still positioned for later readers. Callers own closing it.
    """
    if not path.is_file():
        raise FatalConversionError("INGEST_MISSING", f"EPUB not found: {path}")

    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise FatalConversionError("INGEST_NOT_ZIP", f"Not a ZIP/EPUB archive: {path}") from exc

    names = archive.namelist()
    if len(names) > MAX_ENTRIES:
        archive.close()
        raise FatalConversionError(
            "INGEST_BOMB",
            f"Archive has {len(names)} entries (limit {MAX_ENTRIES})",
        )

    total_uncompressed = 0
    has_encryption = False
    for info in archive.infolist():
        name = info.filename
        if _is_unsafe_name(name):
            archive.close()
            raise FatalConversionError("INGEST_ZIP_SLIP", f"Unsafe archive path: {name}")
        if info.file_size > MAX_SINGLE_MEMBER_BYTES:
            archive.close()
            raise FatalConversionError(
                "INGEST_BOMB",
                f"Member too large ({info.file_size} bytes): {name}",
            )
        total_uncompressed += info.file_size
        if info.compress_size >= MIN_COMPRESSED_FOR_RATIO and info.file_size > 0:
            ratio = info.file_size / max(info.compress_size, 1)
            if ratio > MAX_COMPRESSION_RATIO:
                archive.close()
                raise FatalConversionError(
                    "INGEST_BOMB",
                    f"Compression ratio {ratio:.1f} exceeds limit for {name}",
                )
        if name.replace("\\", "/").rstrip("/") == "META-INF/encryption.xml":
            has_encryption = True

    if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
        archive.close()
        raise FatalConversionError(
            "INGEST_BOMB",
            f"Uncompressed size {total_uncompressed} exceeds {MAX_UNCOMPRESSED_BYTES}",
        )

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
