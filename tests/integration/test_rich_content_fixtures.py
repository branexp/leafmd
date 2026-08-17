"""Characterization tests for the synthetic Phase 4 rich-content EPUB."""

from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

from leafmd.convert import convert_epub
from leafmd.validate.output import validate_book_directory
from tests.fixtures.epub_builder import make_rich_content_book, write_bytes


def _xml_member(archive: zipfile.ZipFile, name: str) -> etree._Element:
    return etree.fromstring(archive.read(name))


def test_rich_fixture_covers_each_source_construct(tmp_path: Path) -> None:
    epub_path = write_bytes(tmp_path / "rich.epub", make_rich_content_book())

    with zipfile.ZipFile(epub_path) as archive:
        assert archive.read("mimetype") == b"application/epub+zip"
        assert archive.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert {"EPUB/rich.xhtml", "EPUB/Notes.xhtml"} <= set(archive.namelist())
        root = _xml_member(archive, "EPUB/rich.xhtml")
        notes = _xml_member(archive, "EPUB/Notes.xhtml")

    assert root.xpath("count(//*[local-name()='table' and @id='rectangular-table'])") == 1
    assert root.xpath("count(//*[local-name()='table' and @id='spanning-table']//*[ @rowspan or @colspan])") == 2
    assert root.xpath("count(//*[local-name()='table' and @id='nested-table']//*[local-name()='table'])") == 1
    assert root.xpath("count(//*[@class='Table'])") == 1
    assert root.xpath("count(//*[@class='Caption'])") == 2
    assert root.xpath("count(//*[@class='Equation'])") == 1
    assert root.xpath("count(//*[local-name()='math'])") == 2
    assert root.xpath("count(//*[local-name()='ruby']/*[local-name()='rt'])") == 1
    assert root.xpath("count(//*[@dir='rtl']//*[local-name()='bdi'])") == 1
    assert root.xpath("count(//*[local-name()='a' and @*[local-name()='type']='noteref'])") == 3
    assert root.xpath("count(//*[@*[local-name()='type']='footnote'])") == 2
    assert notes.xpath("count(//*[@id='cross-note'])") == 1
    assert "Cross-document note text." in "".join(notes.itertext())


def test_rich_fixture_converts_and_validates_as_a_book_directory(tmp_path: Path) -> None:
    epub_path = write_bytes(tmp_path / "rich.epub", make_rich_content_book())
    book_dir, report = convert_epub(epub_path, tmp_path / "out")

    assert report.status in {"ok", "completed_with_warnings"}
    validation = validate_book_directory(book_dir)
    assert not validation.has_fatal()
    assert not validation.has_errors()
    content = "\n".join(path.read_text(encoding="utf-8") for path in (book_dir / "content").glob("*.md"))
    for marker in ("rectangular", "North", "cross-document", "漢字", "مرحبا", "wrapped equation"):
        assert marker in content
