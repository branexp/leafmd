from pathlib import Path

from leafmd.convert import convert_epub
from leafmd.validate.output import validate_book_directory
from tests.fixtures.epub_builder import make_custom_epub3, make_epub2, make_epub3, make_xxe, write_bytes


def test_convert_epub3(tmp_path: Path) -> None:
    epub = write_bytes(tmp_path / "book3.epub", make_epub3())
    out = tmp_path / "out3"
    book_dir, report = convert_epub(epub, out)
    assert report.status in {"ok", "completed_with_warnings"}
    assert (book_dir / "book.json").is_file()
    assert (book_dir / "toc.json").is_file()
    assert (book_dir / "conversion-report.json").is_file()
    assert (book_dir / "index.md").is_file()
    assert (book_dir / "toc.md").is_file()
    chapters = list((book_dir / "content").glob("*.md"))
    assert len(chapters) == 2
    text = "\n".join(path.read_text(encoding="utf-8") for path in chapters)
    assert "Hello from chapter one." in text
    assert "src-ch01-p1" in text or "src-ch01-welcome" in text
    assert (book_dir / "assets" / "images" / "pic.svg").is_file()
    assert (book_dir / "assets" / "images" / "cover.png").is_file()
    validation = validate_book_directory(book_dir)
    assert not validation.has_fatal()
    assert not validation.has_errors()


def test_convert_epub2(tmp_path: Path) -> None:
    epub = write_bytes(tmp_path / "book2.epub", make_epub2())
    book_dir, report = convert_epub(epub, tmp_path / "out2")
    assert report.status in {"ok", "completed_with_warnings"}
    chapters = list((book_dir / "content").glob("*.md"))
    assert len(chapters) == 1
    assert "EPUB 2 body text." in chapters[0].read_text(encoding="utf-8")
    assert (book_dir / "assets" / "images" / "cover.png").is_file()


def test_xxe_does_not_expand_passwd(tmp_path: Path) -> None:
    epub = write_bytes(tmp_path / "xxe.epub", make_xxe())
    book_dir, _report = convert_epub(epub, tmp_path / "out-xxe")
    text = (next((book_dir / "content").glob("*.md"))).read_text(encoding="utf-8")
    assert "root:" not in text


def test_broken_link_is_reported(tmp_path: Path) -> None:
    epub = write_bytes(tmp_path / "broken.epub", make_epub3(broken_link=True))
    _book_dir, report = convert_epub(epub, tmp_path / "out-broken")
    codes = {issue.code for issue in report.issues}
    assert "LINK_UNRESOLVED" in codes


def test_unicode_and_mojibake_are_rendered_conservatively(tmp_path: Path) -> None:
    epub = write_bytes(
        tmp_path / "unicode.epub",
        make_custom_epub3(
            title="Unicode",
            chapters=[
                (
                    "ch01",
                    "ch01.xhtml",
                    "<h1>Unicode</h1><p>Café — ▪ Tarâscon Â  CafÃ©</p>",
                )
            ],
        ),
    )
    book_dir, _report = convert_epub(epub, tmp_path / "out-unicode")
    text = next((book_dir / "content").glob("*.md")).read_text(encoding="utf-8")
    assert "Café — ▪ Tarâscon" in text
    assert "CafÃ©" not in text
    assert "Â" not in text
