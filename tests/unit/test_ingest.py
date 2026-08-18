from pathlib import Path

import pytest

from leafmd.errors import FatalConversionError
from leafmd.ingest.archive import inspect_epub_archive
from leafmd.report import new_report
from tests.fixtures.epub_builder import make_drm, make_unusual_member_name, write_bytes


def test_unusual_member_names_are_not_extracted_or_filtered(tmp_path: Path) -> None:
    path = write_bytes(tmp_path / "unusual.epub", make_unusual_member_name())
    archive = inspect_epub_archive(path, new_report())
    try:
        assert "../evil.txt" in archive.namelist()
    finally:
        archive.close()


def test_invalid_zip_rejected(tmp_path: Path) -> None:
    path = write_bytes(tmp_path / "invalid.epub", b"not a ZIP")
    with pytest.raises(FatalConversionError) as exc:
        inspect_epub_archive(path, new_report())
    assert exc.value.code == "INGEST_NOT_ZIP"


def test_drm_rejected(tmp_path: Path) -> None:
    path = write_bytes(tmp_path / "drm.epub", make_drm())
    with pytest.raises(FatalConversionError) as exc:
        inspect_epub_archive(path, new_report())
    assert exc.value.code == "INGEST_DRM"
