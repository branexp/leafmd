from leafmd.convert import convert_epub
from leafmd.model.issues import IssueSeverity
from leafmd.model.section import OutputTarget
from leafmd.report import new_report
from leafmd.transform.links import TargetMap, _rewrite_href
from tests.fixtures.epub_builder import (
    make_custom_epub3,
    make_duplicate_id_book,
    make_fragment_book,
    make_scheme_book,
    write_bytes,
)


def _codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def test_same_file_and_cross_file_fragments(tmp_path) -> None:
    epub = write_bytes(tmp_path / "fragments.epub", make_fragment_book())
    book_dir, report = convert_epub(epub, tmp_path / "out-fragments")
    assert "LINK_UNRESOLVED" not in _codes(report)
    chapter_one = next(path for path in (book_dir / "content").glob("*.md") if "chapter-1" in path.name)
    chapter_two = next(path for path in (book_dir / "content").glob("*.md") if "chapter-2" in path.name)
    text_one = chapter_one.read_text(encoding="utf-8")
    text_two = chapter_two.read_text(encoding="utf-8")
    assert 'id="src-ch01-here"' in text_one
    assert 'id="src-ch02-there"' in text_two
    assert f"{chapter_two.name}#src-ch02-there" in text_one
    assert 'id="src-ch01-welcome"' in text_one
    toc = (book_dir / "toc.md").read_text(encoding="utf-8")
    assert "src-ch01-welcome" in toc
    assert "src-ch02-there" in toc


def test_duplicate_source_ids_are_reported_and_first_wins(tmp_path) -> None:
    epub = write_bytes(tmp_path / "dups.epub", make_duplicate_id_book())
    book_dir, report = convert_epub(epub, tmp_path / "out-dups")
    assert "ANCHOR_SOURCE_DUP" in _codes(report)
    first = next(path for path in (book_dir / "content").glob("*.md") if path.name.startswith("001-"))
    second = next(path for path in (book_dir / "content").glob("*.md") if path.name.startswith("002-"))
    first_text = first.read_text(encoding="utf-8")
    second_text = second.read_text(encoding="utf-8")
    assert first_text.count('id="src-ch01-dup"') == 1
    assert 'id="src-ch02-dup"' in second_text
    assert f"{first.name}#src-ch01-dup" in second_text


def test_unsafe_schemes_are_dropped(tmp_path) -> None:
    epub = write_bytes(tmp_path / "schemes.epub", make_scheme_book())
    book_dir, report = convert_epub(epub, tmp_path / "out-schemes")
    assert "LINK_SCHEME_DROPPED" in _codes(report)
    text = next((book_dir / "content").glob("*.md")).read_text(encoding="utf-8")
    assert "javascript:" not in text
    assert "data:text/html" not in text
    assert "file:///etc/passwd" not in text
    assert "https://example.com" in text
    dropped = [issue for issue in report.issues if issue.code == "LINK_SCHEME_DROPPED"]
    assert {issue.severity for issue in dropped} == {IssueSeverity.WARNING}
    assert len(dropped) == 3


def test_colon_in_filename_is_not_a_scheme() -> None:
    report = new_report()
    targets = TargetMap(
        by_href={
            ("EPUB/Text/Chapter 1: Intro.xhtml", None): OutputTarget(path="content/001.md", anchor=None),
            ("EPUB/Text/ch02.xhtml", None): OutputTarget(path="content/002.md", anchor=None),
        }
    )
    same_dir = _rewrite_href(
        "Chapter 1: Intro.xhtml",
        "EPUB/Text/ch02.xhtml",
        targets,
        report,
        "content/002.md",
    )
    nested = _rewrite_href(
        "Text/Chapter 1: Intro.xhtml",
        "EPUB/nav.xhtml",
        targets,
        report,
        "content/002.md",
    )
    assert same_dir == "001.md"
    assert nested == "001.md"
    assert "LINK_SCHEME_DROPPED" not in {issue.code for issue in report.issues}


def test_colon_in_filename_survives_convert(tmp_path) -> None:
    epub = write_bytes(
        tmp_path / "colon.epub",
        make_custom_epub3(
            title="Colon",
            chapters=[
                ("ch01", "Text/Chapter 1: Intro.xhtml", "<h1>Intro</h1><p>target</p>"),
                (
                    "ch02",
                    "Text/ch02.xhtml",
                    '<h1>Next</h1><p><a href="Chapter 1: Intro.xhtml">back</a></p>',
                ),
            ],
        ),
    )
    book_dir, report = convert_epub(epub, tmp_path / "out-colon")
    assert "LINK_SCHEME_DROPPED" not in _codes(report)
    second = next(path for path in (book_dir / "content").glob("002-*.md"))
    assert "001-" in second.read_text(encoding="utf-8")
