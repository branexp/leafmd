"""P2-5 characterization of planner cases B/C. Phase 3 implements the heuristics."""

from __future__ import annotations

from leafmd.convert import convert_epub
from tests.fixtures.epub_builder import (
    make_many_headings_one_file,
    make_split_chapter_files,
    make_virtual_part_book,
    write_bytes,
)


def test_case_c_one_file_many_chapters_is_split(tmp_path) -> None:
    epub = write_bytes(tmp_path / "many.epub", make_many_headings_one_file())
    book_dir, _report = convert_epub(epub, tmp_path / "out-many")
    chapters = list((book_dir / "content").glob("*.md"))
    assert len(chapters) == 2


def test_case_c_desired_split(tmp_path) -> None:
    epub = write_bytes(tmp_path / "many.epub", make_many_headings_one_file())
    book_dir, _report = convert_epub(epub, tmp_path / "out-desired-c")
    titles = [path.read_text(encoding="utf-8") for path in (book_dir / "content").glob("*.md")]
    assert len(titles) == 2


def test_case_b_many_files_one_nav_entry_merge(tmp_path) -> None:
    epub = write_bytes(tmp_path / "split.epub", make_split_chapter_files())
    book_dir, _report = convert_epub(epub, tmp_path / "out-split")
    assert len(list((book_dir / "content").glob("*.md"))) == 1


def test_case_b_desired_merge(tmp_path) -> None:
    epub = write_bytes(tmp_path / "split.epub", make_split_chapter_files())
    book_dir, _report = convert_epub(epub, tmp_path / "out-desired-b")
    chapters = list((book_dir / "content").glob("*.md"))
    assert len(chapters) == 1
    text = chapters[0].read_text(encoding="utf-8")
    assert "part a" in text
    assert "part b of the same chapter" in text


def test_virtual_part_has_no_section_file(tmp_path) -> None:
    epub = write_bytes(tmp_path / "part.epub", make_virtual_part_book())
    book_dir, _report = convert_epub(epub, tmp_path / "out-part")
    files = list((book_dir / "content").glob("*.md"))
    assert len(files) == 2
    toc = (book_dir / "toc.md").read_text(encoding="utf-8")
    assert "Part I" in toc


def test_virtual_part_desired_tree(tmp_path) -> None:
    import json

    epub = write_bytes(tmp_path / "part.epub", make_virtual_part_book())
    book_dir, _report = convert_epub(epub, tmp_path / "out-desired-part")
    toc = json.loads((book_dir / "toc.json").read_text(encoding="utf-8"))
    assert toc["nodes"][0]["title"] == "Part I"
    assert toc["nodes"][0]["section_id"] is None
    assert len(toc["nodes"][0]["children"]) == 2
