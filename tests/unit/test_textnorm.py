from leafmd.transform.textnorm import (
    description_to_markdown,
    drop_caps,
    join_line_hyphens,
    normalize_text,
    promote_leading_bold_title,
)


def test_drop_caps_markdown_and_html() -> None:
    assert drop_caps("**T**hen") == "Then"
    assert drop_caps("***T**hunder") == "Thunder"
    assert drop_caps('<span class="dropcap">T</span>hen') == "Then"
    assert drop_caps("<b>T</b>hen") == "Then"


def test_join_only_line_hyphenation() -> None:
    assert join_line_hyphens("inter- national") == "international"
    assert join_line_hyphens("Zodiac- and") == "Zodiac- and"
    assert join_line_hyphens("IXX- title") == "IXX- title"


def test_no_ocr_rewriting() -> None:
    assert normalize_text("tluee modem") == "tluee modem"


def test_leading_bold_title_promotion() -> None:
    assert promote_leading_bold_title("**Chapter One**\n\nBody") == "# Chapter One\n\nBody"
    assert promote_leading_bold_title("# Existing\n\n**Title**") == "# Existing\n\n**Title**"


def test_description_html_to_markdown() -> None:
    assert description_to_markdown("<p>Hello <em>world</em><br>Again <strong>now</strong>.</p>") == (
        "Hello *world*\nAgain **now**."
    )
    assert description_to_markdown("<p>Keep <span>text</span>; <u>strip</u> tags.</p>") == ("Keep text; strip tags.")
