from lxml import etree

from leafmd.transform.notes import NoteClass, analyze_notes, sanitize_label


def parse(body: str) -> etree._Element:
    return etree.fromstring(f'<html xmlns:epub="http://www.idpf.org/2007/ops"><body>{body}</body></html>')


def test_standard_epub_note_is_simple_and_deterministic() -> None:
    root = parse(
        '<p id="p"><a id="r" epub:type="noteref" href="#n"><sup>1</sup></a></p>'
        '<aside id="n" epub:type="footnote">A short note.</aside>'
    )
    result = analyze_notes(root, "Text/Chapter.xhtml")
    assert len(result.references) == 1
    assert len(result.definitions) == 1
    assert result.relationships[0].classification is NoteClass.SIMPLE_LOCAL
    assert result.relationships[0].label == analyze_notes(root, "Text/Chapter.xhtml").relationships[0].label


def test_role_metadata_and_cross_document_are_preserved() -> None:
    root = parse('<a id="r" role="doc-noteref" href="Notes.xhtml#n">*</a>')
    root.append(etree.fromstring('<aside id="n" role="doc-footnote">Note</aside>'))
    result = analyze_notes(root, "Text/Chapter.xhtml")
    assert result.relationships[0].classification is NoteClass.CROSS_DOCUMENT


def test_publisher_superscript_fallback() -> None:
    root = parse(
        '<p><a id="s1" href="#fn1"><sup>1</sup></a></p><div id="fn1">Definition <a href="#s1">return</a></div>'
    )
    result = analyze_notes(root, "chapter.xhtml")
    assert result.relationships[0].classification is NoteClass.SIMPLE_LOCAL
    assert result.relationships[0].definition_id == "fn1"


def test_missing_or_ambiguous_target_is_not_footnote() -> None:
    root = parse('<a epub:type="noteref" href="#missing">1</a><aside id="one" epub:type="footnote">one</aside>')
    result = analyze_notes(root)
    assert result.relationships[0].classification is NoteClass.AMBIGUOUS


def test_rich_definition_is_complex_and_section_boundary_is_explicit() -> None:
    root = parse('<a epub:type="noteref" href="#n">1</a><aside id="n" epub:type="footnote"><p>block note</p></aside>')
    assert analyze_notes(root).relationships[0].classification is NoteClass.COMPLEX
    assert analyze_notes(root, same_section=False).relationships[0].classification is NoteClass.COMPLEX


def test_label_sanitization_does_not_depend_on_order() -> None:
    assert sanitize_label("Text/Chapter 1.xhtml", "N 01") == "note-text-chapter-1-xhtml-n-01"
    assert sanitize_label("", "!!!") == "note-fallback"
