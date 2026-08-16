from pathlib import Path

import pytest

from leafmd.errors import FatalConversionError
from leafmd.ingest.archive import inspect_epub_archive
from leafmd.report import new_report
from tests.fixtures.epub_builder import make_drm, make_zip_slip, write_bytes


def test_zip_slip_rejected(tmp_path: Path) -> None:
    path = write_bytes(tmp_path / "slip.epub", make_zip_slip())
    with pytest.raises(FatalConversionError) as exc:
        inspect_epub_archive(path, new_report())
    assert exc.value.code == "INGEST_ZIP_SLIP"


def test_drm_rejected(tmp_path: Path) -> None:
    path = write_bytes(tmp_path / "drm.epub", make_drm())
    with pytest.raises(FatalConversionError) as exc:
        inspect_epub_archive(path, new_report())
    assert exc.value.code == "INGEST_DRM"
