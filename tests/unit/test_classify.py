from leafmd.model.publication import Resource
from leafmd.semantics.classify import classify_from_title, classify_section


def test_classify_preface() -> None:
    resource = Resource(id="pref", href="preface.xhtml", media_type="application/xhtml+xml")
    semantic_type, evidence = classify_from_title("Preface", resource)
    assert semantic_type == "preface"
    assert evidence[0].source == "heading"


def test_preface_heading_beats_generic_book_title() -> None:
    resource = Resource(id="prf", href="prf.xhtml", media_type="application/xhtml+xml")
    semantic_type, evidence = classify_section("My Book", resource, headings=("Preface",), book_title="My Book")
    assert semantic_type == "preface"
    assert evidence[0].source == "heading"


def test_cover_from_filename_and_dot_title() -> None:
    resource = Resource(id="cover", href="cover.xhtml", media_type="application/xhtml+xml")
    semantic_type, evidence = classify_section(".", resource, book_title="My Book")
    assert semantic_type == "cover"
    assert evidence[0].source == "filename"


def test_about_author_from_filename() -> None:
    resource = Resource(id="ata", href="ata.xhtml", media_type="application/xhtml+xml")
    semantic_type, _ = classify_section("My Book", resource, book_title="My Book")
    assert semantic_type == "about-author"


def test_back_matter_ads_are_other() -> None:
    resource = Resource(id="bm1", href="bm1.xhtml", media_type="application/xhtml+xml")
    semantic_type, _ = classify_section("Books by the Author", resource)
    assert semantic_type == "other"


def test_real_chapter_title_defaults_to_chapter() -> None:
    resource = Resource(id="x", href="x.xhtml", media_type="application/xhtml+xml")
    semantic_type, evidence = classify_section("The Long Road", resource, book_title="My Book")
    assert semantic_type == "chapter"
    assert evidence[0].source == "spine"


def test_evidence_precedence() -> None:
    resource = Resource(
        id="cover",
        href="cover.xhtml",
        media_type="application/xhtml+xml",
        properties=frozenset({"cover-image"}),
    )
    semantic_type, evidence = classify_section(
        "Chapter 1", resource, landmark="index", nav_label="Preface", headings=("Preface",)
    )
    assert semantic_type == "cover"
    assert evidence[0].source == "epub:type"


def test_index_continuation_uses_sibling_evidence() -> None:
    resource = Resource(id="in1_b", href="in1_b.xhtml", media_type="application/xhtml+xml")
    semantic_type, _ = classify_section("My Book", resource, sibling_types=("index",))
    assert semantic_type == "index"


def test_generic_book_title_is_not_chapter() -> None:
    resource = Resource(id="x", href="x.xhtml", media_type="application/xhtml+xml")
    semantic_type, _ = classify_from_title("My Book", resource, book_title="My Book")
    assert semantic_type == "other"


def test_empty_title_is_not_chapter() -> None:
    resource = Resource(id="x", href="x.xhtml", media_type="application/xhtml+xml")
    semantic_type, _ = classify_from_title("", resource)
    assert semantic_type == "other"


def test_guide_type_has_priority_over_heading() -> None:
    resource = Resource(id="x", href="x.xhtml", media_type="application/xhtml+xml")
    semantic_type, evidence = classify_section("Chapter 1", resource, guide_type="preface")
    assert semantic_type == "preface"
    assert evidence[0].source == "guide"


def test_guide_cover_type_maps_without_regex() -> None:
    resource = Resource(id="cvi", href="cover.xhtml", media_type="application/xhtml+xml")
    semantic_type, evidence = classify_section(
        ".", resource, guide_type="other.ms-coverimage-standard", book_title="My Book"
    )
    assert semantic_type == "cover"
    assert evidence[0].source == "guide"


def test_numbered_title_beats_later_introduction_heading() -> None:
    resource = Resource(id="c14", href="c14.xhtml", media_type="application/xhtml+xml")
    semantic_type, evidence = classify_section(
        "XIV - Pythagorean Mathematics",
        resource,
        headings=("XIV", "Introduction"),
    )
    assert semantic_type == "chapter"
    assert evidence[0].source == "title"


def test_table_of_contents_is_other() -> None:
    resource = Resource(id="toc", href="toc.xhtml", media_type="application/xhtml+xml")
    semantic_type, _ = classify_section("Table of Contents", resource)
    assert semantic_type == "other"
