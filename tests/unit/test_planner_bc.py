"""P2-5 characterization of planner cases B/C. Phase 3 implements the heuristics."""

from __future__ import annotations

from leafmd.convert import convert_epub
from leafmd.model.publication import Resource
from leafmd.parse.navigation import parse_html_toc
from tests.fixtures.epub_builder import (
    make_custom_epub3,
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


def test_case_c_toc_json_keeps_fragment_section_ids(tmp_path) -> None:
    import json

    epub = write_bytes(tmp_path / "many.epub", make_many_headings_one_file())
    book_dir, _report = convert_epub(epub, tmp_path / "out-toc-c")
    toc = json.loads((book_dir / "toc.json").read_text(encoding="utf-8"))
    assert [node["section_id"] for node in toc["nodes"]] == ["sec-001", "sec-002"]


def test_case_b_desired_merge(tmp_path) -> None:
    epub = write_bytes(tmp_path / "split.epub", make_split_chapter_files())
    book_dir, _report = convert_epub(epub, tmp_path / "out-desired-b")
    chapters = list((book_dir / "content").glob("*.md"))
    assert len(chapters) == 1
    text = chapters[0].read_text(encoding="utf-8")
    assert "part a" in text
    assert "part b of the same chapter" in text


def test_case_b_keeps_distinct_front_matter_separate(tmp_path) -> None:
    epub = write_bytes(
        tmp_path / "front-matter.epub",
        make_custom_epub3(
            title="Front Matter",
            chapters=[
                ("ded", "ded.xhtml", "<h1>Dedication</h1><p>For readers.</p>"),
                ("prf", "prf.xhtml", "<h1>Preface</h1><p>For context.</p>"),
            ],
            nav_items=[("Dedication", "ded.xhtml")],
        ),
    )
    book_dir, _report = convert_epub(epub, tmp_path / "out-front-matter")
    sections = (book_dir / "book.json").read_text(encoding="utf-8")
    assert sections.count('"type": "dedication"') == 1
    assert sections.count('"type": "preface"') == 1


def test_html_toc_filename_is_detected() -> None:
    from leafmd.semantics.plan import _looks_like_toc

    resource = Resource(id="toc", href="toc.xhtml", media_type="application/xhtml+xml")
    assert _looks_like_toc(resource)


def test_html_toc_extracts_relative_links() -> None:
    resource = Resource(
        id="toc",
        href="OEBPS/toc.xhtml",
        media_type="application/xhtml+xml",
        content=(
            b'<html xmlns="http://www.w3.org/1999/xhtml"><body>'
            b"<div>Table of Contents</div>"
            b'<a href="chapter.xhtml">Chapter One</a>'
            b'<a href="chapter.xhtml#part2">Part Two</a>'
            b'<a href="https://example.test/out">External</a>'
            b"</body></html>"
        ),
    )
    nodes = parse_html_toc(resource)
    assert [(node.title, node.href) for node in nodes] == [
        ("Chapter One", "OEBPS/chapter.xhtml"),
        ("Part Two", "OEBPS/chapter.xhtml#part2"),
    ]


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


def test_overlapping_nav_and_ncx_fragments_are_not_sliced_twice() -> None:
    from leafmd.model.publication import BookMetadata, NavNode, NormalizedPublication, Resource, SpineEntry
    from leafmd.report import new_report
    from leafmd.semantics.plan import plan_sections

    html = (
        b'<html xmlns="http://www.w3.org/1999/xhtml"><body>'
        b'<h1 id="c1">One</h1><p>first</p>'
        b'<h1 id="c2">Two</h1><p>second</p>'
        b"</body></html>"
    )
    resource = Resource(id="all", href="all.xhtml", media_type="application/xhtml+xml", content=html)
    publication = NormalizedPublication(
        schema_version=1,
        metadata=BookMetadata(title="Overlap"),
        epub_version="3.0",
        package_path="content.opf",
        source_filename="overlap.epub",
        resources={"all": resource},
        spine=[SpineEntry(idref="all", linear=True, href="all.xhtml")],
        nav_toc=[
            NavNode("One", "all.xhtml#c1", "toc"),
            NavNode("Two", "all.xhtml#c2", "toc"),
        ],
        ncx_toc=[
            NavNode("One NCX", "all.xhtml#c1", "ncx"),
            NavNode("Two NCX", "all.xhtml#c2", "ncx"),
        ],
        landmarks=[],
        guide=[],
    )
    plans = plan_sections(publication, new_report())
    assert [plan.title for plan in plans] == ["One", "Two"]
