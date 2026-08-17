from lxml import etree

from leafmd.model.section import SectionPlan, SourceRange
from leafmd.render.markdown import render_section


def render(body: str, href: str = "Chapter.xhtml") -> str:
    root = etree.fromstring(f'<html xmlns:epub="http://www.idpf.org/2007/ops"><body>{body}</body></html>'.encode())
    plan = SectionPlan("chapter", "Chapter", "chapter", "file", [SourceRange(href)], [], [], 1)
    return render_section(root, plan, {})


def test_safe_table_caption_is_gfm_and_not_duplicated() -> None:
    output = render(
        "<table><caption>Table 1: Values</caption><thead><tr><th>A</th><th>B</th></tr></thead>"
        "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
    )
    assert output.count("Table 1: Values") == 1
    assert "| A | B |" in output and "| 1 | 2 |" in output


def test_spanning_and_block_tables_remain_raw_html() -> None:
    output = render('<table><tr><th>A</th></tr><tr><td colspan="2"><p>block</p></td></tr></table>')
    assert '<table><tr><th>A</th></tr><tr><td colspan="2"><p>block</p></td></tr></table>' in output


def test_simple_local_note_becomes_deterministic_footnote() -> None:
    output = render(
        '<p>Text <a id="ref" epub:type="noteref" href="#note"><sup>1</sup></a>.</p>'
        '<aside id="note" epub:type="footnote">A short note.</aside>'
    )
    assert "Text [^note-chapter-xhtml-ref]." in output
    assert "[^note-chapter-xhtml-ref]: A short note." in output
    assert 'href="#note"' not in output


def test_complex_and_cross_document_notes_keep_links() -> None:
    complex_note = render(
        '<p><a id="ref" epub:type="noteref" href="#note">1</a></p>'
        '<aside id="note" epub:type="footnote"><p>Block note</p></aside>'
    )
    cross_document = render(
        '<p><a id="ref" epub:type="noteref" href="Notes.xhtml#note">1</a></p>'
        '<aside id="note" epub:type="footnote">Remote note</aside>'
    )
    assert "[^" not in complex_note and "#note" in complex_note
    assert "[^" not in cross_document and "Notes.xhtml#note" in cross_document


def test_mathml_ruby_bidi_and_unsafe_rich_content() -> None:
    output = render(
        '<p><math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mi>x-</mi></math>'
        '<ruby><rb>漢字</rb><rt>かんじ</rt></ruby><bdi dir="rtl">שלום</bdi></p>'
        '<script>alert(1)</script><math onclick="bad" href="javascript:bad"><mi>y</mi></math>'
    )
    assert "<math" in output and 'display="block"' in output and "x-" in output
    assert "<ruby" in output and "<rt>かんじ</rt>" in output and 'dir="rtl"' in output
    assert "script" not in output.lower() and "onclick" not in output and "javascript:" not in output


def test_rendering_is_deterministic() -> None:
    body = "<p>Wrapped hy-\nphen</p><table><tr><th>A</th></tr><tr><td>x</td></tr></table>"
    assert render(body) == render(body)


def test_source_line_wrapping_collapses_inside_paragraphs() -> None:
    output = render("<p>One\n  two<br/>three</p><p>Next\nline</p>")
    content = output.split("---\n\n", 1)[1]
    assert content == "One two  \nthree\n\nNext line\n"
