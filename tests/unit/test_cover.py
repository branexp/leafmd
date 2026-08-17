import json

from leafmd.convert import convert_epub
from tests.fixtures.epub_builder import (
    make_epub2,
    make_epub3,
    make_guide_cover_book,
    write_bytes,
)


def test_guide_only_image_cover_is_recorded_and_copied(tmp_path) -> None:
    epub = write_bytes(tmp_path / "guide.epub", make_guide_cover_book(jpeg=True))
    book_dir, report = convert_epub(epub, tmp_path / "out")

    book = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    assert book["cover"] is not None
    assert book["cover"]["source_href"] == "EPUB/cover.jpg"
    assert (book_dir / "assets/images/cover.jpg").is_file()
    assert not any(issue.code == "COVER_MISSING" for issue in report.issues)


def test_guide_xhtml_cover_follows_first_local_image(tmp_path) -> None:
    epub = write_bytes(tmp_path / "guide-xhtml.epub", make_guide_cover_book(xhtml_cover=True))
    book_dir, _report = convert_epub(epub, tmp_path / "out-xhtml")

    book = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    assert book["cover"]["source_href"] == "EPUB/cover.png"
    assert (book_dir / "assets/images/cover.png").is_file()


def test_existing_epub2_and_epub3_covers_are_recorded_and_copied(tmp_path) -> None:
    epub2 = write_bytes(tmp_path / "book2.epub", make_epub2())
    book2, _report2 = convert_epub(epub2, tmp_path / "out2")
    assert json.loads((book2 / "book.json").read_text())["cover"] is not None
    assert (book2 / "assets/images/cover.png").is_file()

    epub3 = write_bytes(tmp_path / "book3.epub", make_epub3())
    book3, _report3 = convert_epub(epub3, tmp_path / "out3")
    assert json.loads((book3 / "book.json").read_text())["cover"] is not None
    assert (book3 / "assets/images/cover.png").is_file()
