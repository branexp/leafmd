"""Characterization tests for the synthetic Phase 4 rich-content EPUB."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from lxml import etree

from leafmd.convert import convert_epub
from leafmd.validate.output import validate_book_directory
from tests.fixtures.epub_builder import make_custom_epub3, make_rich_content_book, write_bytes


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

    assert report.status == "ok"
    assert report.stats.unresolved_links == 0
    validation = validate_book_directory(book_dir)
    assert not validation.has_fatal()
    assert not validation.has_errors()
    content = "\n".join(path.read_text(encoding="utf-8") for path in (book_dir / "content").glob("*.md"))
    for marker in ("rectangular", "North", "cross-document", "漢字", "مرحبا", "wrapped equation"):
        assert marker in content
    assert 'rowspan="2"' in content and '<table id="nested-table">' in content
    assert "<math" in content and "<ruby" in content and 'dir="auto"' in content
    assert "[^note-epub-rich-xhtml-local-note]" in content
    assert "[^note-epub-rich-xhtml-local-note]:" in content
    assert "#src-notes-cross-note" in content and "#src-rich-cross-ref" in content
    assert "](#)" not in content


def test_rich_conversion_is_byte_stable_and_report_schema_compatible(tmp_path: Path) -> None:
    epub_path = write_bytes(tmp_path / "rich.epub", make_rich_content_book())
    first, first_report = convert_epub(epub_path, tmp_path / "first")
    second, second_report = convert_epub(epub_path, tmp_path / "second")

    first_files = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
    second_files = sorted(path.relative_to(second) for path in second.rglob("*") if path.is_file())
    assert first_files == second_files
    assert [path.read_bytes() for path in (first / file for file in first_files)] == [
        path.read_bytes() for path in (second / file for file in second_files)
    ]
    assert first_report.stats.to_dict() == second_report.stats.to_dict()
    report = json.loads((first / "conversion-report.json").read_text(encoding="utf-8"))
    assert report["stats"].keys() == {
        "source_documents",
        "generated_files",
        "images_copied",
        "unresolved_links",
        "assets_skipped",
    }
    assert json.loads((first / "book.json").read_text(encoding="utf-8"))["schema_version"] == 1


def test_rich_pipeline_rewrites_cross_document_note_and_validates_footnotes(tmp_path: Path) -> None:
    epub = make_custom_epub3(
        title="Cross-document notes",
        chapters=[
            (
                "rich",
                "rich.xhtml",
                '<h1 id="cross-ref">Text</h1>'
                '<p><a epub:type="noteref" href="Notes.xhtml#cross-note">cross-note</a></p>',
            ),
            (
                "notes",
                "Notes.xhtml",
                '<h1 id="notes">Notes</h1><aside id="cross-note" epub:type="footnote">Cross note</aside>',
            ),
        ],
        spine=[("rich", True), ("notes", False)],
    )
    book, report = convert_epub(write_bytes(tmp_path / "cross.epub", epub), tmp_path / "cross-out")
    assert report.stats.unresolved_links == 0
    assert not validate_book_directory(book).has_errors()
    rich = next((book / "content").glob("001-*.md")).read_text(encoding="utf-8")
    notes = next((book / "content").glob("002-*.md")).read_text(encoding="utf-8")
    assert "002-" in rich and "#src-notes-cross-note" in rich
    assert 'id="src-notes-cross-note"' in notes


def test_validator_rejects_dangling_gfm_footnote_reference(tmp_path: Path) -> None:
    epub_path = write_bytes(tmp_path / "rich.epub", make_rich_content_book())
    book, _ = convert_epub(epub_path, tmp_path / "out")
    content = next((book / "content").glob("*.md"))
    content.write_text(content.read_text(encoding="utf-8") + "\nDangling[^missing].\n", encoding="utf-8")
    validation = validate_book_directory(book)
    assert any(issue.code == "VALIDATE_FOOTNOTE_MISSING" for issue in validation.issues)
