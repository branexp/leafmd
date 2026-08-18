from lxml import etree

from leafmd.images.transform import apply_image_conversions
from leafmd.model.images import ImageAnalysis, ImageBlock, ImageBlockKind, ImageDecision
from leafmd.report import new_report


def _analysis(*blocks: ImageBlock) -> ImageAnalysis:
    return ImageAnalysis(
        source_href="EPUB/images/scan.png",
        decision=ImageDecision.REPLACE,
        blocks=tuple(blocks),
        labels=tuple(block.label for block in blocks),
        reason="markdown-representable",
        backend="test",
    )


def test_image_only_paragraph_becomes_text_and_preserves_id() -> None:
    root = etree.fromstring(b'<html><body><p id="scan"><img src="images/scan.png"/></p></body></html>')
    analysis = _analysis(ImageBlock(ImageBlockKind.TEXT, "Recovered text", "text"))
    report = new_report()
    apply_image_conversions(root, "EPUB/ch.xhtml", {analysis.source_href: analysis}, report)
    paragraph = root.xpath(".//p")[0]
    assert paragraph.get("id") == "scan"
    assert paragraph.text == "Recovered text"
    assert root.xpath(".//img") == []
    assert report.stats.image_replacements == 1


def test_inline_text_image_is_preserved() -> None:
    root = etree.fromstring(b'<html><body><p>Before <img src="images/scan.png"/> after.</p></body></html>')
    analysis = _analysis(ImageBlock(ImageBlockKind.TEXT, "Recovered text", "text"))
    apply_image_conversions(root, "EPUB/ch.xhtml", {analysis.source_href: analysis}, new_report())
    assert len(root.xpath(".//img")) == 1


def test_inline_formula_is_replaced_with_formula_marker() -> None:
    root = etree.fromstring(b'<html><body><p>Before <img src="images/scan.png"/> after.</p></body></html>')
    analysis = _analysis(ImageBlock(ImageBlockKind.FORMULA, "x^2", "formula"))
    apply_image_conversions(root, "EPUB/ch.xhtml", {analysis.source_href: analysis}, new_report())
    span = root.xpath(".//span")[0]
    assert span.text == "$x^2$"
    assert span.tail == " after."


def test_unsafe_table_markup_is_stripped_before_insertion() -> None:
    root = etree.fromstring(b'<html><body><p><img src="images/scan.png"/></p></body></html>')
    html = '<table onclick="evil()"><tr><th>A</th></tr><tr><td rowspan="2">1<script>bad()</script></td></tr></table>'
    analysis = _analysis(ImageBlock(ImageBlockKind.TABLE, html, "table"))
    apply_image_conversions(root, "EPUB/ch.xhtml", {analysis.source_href: analysis}, new_report())
    table = root.xpath(".//table")[0]
    assert "onclick" not in table.attrib
    assert root.xpath(".//script") == []
    assert root.xpath(".//td")[0].get("rowspan") == "2"


def test_existing_figcaption_suppresses_recovered_caption() -> None:
    root = etree.fromstring(
        b"<html><body><figure><img src='images/scan.png'/><figcaption>Publisher caption</figcaption>"
        b"</figure></body></html>"
    )
    analysis = _analysis(
        ImageBlock(ImageBlockKind.TEXT, "OCR caption", "figure_caption"),
        ImageBlock(ImageBlockKind.TEXT, "Recovered body", "text"),
    )
    apply_image_conversions(root, "EPUB/ch.xhtml", {analysis.source_href: analysis}, new_report())
    text = " ".join("".join(root.itertext()).split())
    assert "OCR caption" not in text
    assert "Recovered body" in text
    assert "Publisher caption" in text
