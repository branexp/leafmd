from lxml import etree

from leafmd.transform.tables import TableKind, classify_table, normalize_table


def table(markup: str) -> etree._Element:
    return etree.fromstring(markup.encode())


def test_rectangular_table_with_explicit_header_is_gfm_safe() -> None:
    decision = classify_table(
        table("<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>")
    )
    assert decision.kind is TableKind.GFM
    assert decision.gfm_safe
    assert decision.rows == 2
    assert decision.columns == 2
    assert decision.reason == "rectangular-inline-safe"


def test_missing_or_ambiguous_header_is_raw_html() -> None:
    missing = classify_table(table("<table><tr><td>A</td></tr></table>"))
    ambiguous = classify_table(table("<table><thead><tr><th>A</th></tr></thead><tr><th>B</th></tr></table>"))
    assert missing.reason == "missing-predictable-header"
    assert ambiguous.reason == "ambiguous-header"
    assert missing.preserve_as_raw_html


def test_spans_are_preserved_and_never_flattened() -> None:
    source = table("<table><tr><th>A</th><th>B</th></tr><tr><td colspan='2'>x</td></tr></table>")
    decision = classify_table(source)
    assert decision.kind is TableKind.RAW_HTML
    assert decision.reason == "rowspan-or-colspan"
    assert decision.source_table.xpath(".//td/@colspan") == ["2"]
    assert decision.normalized_table.xpath(".//td/@colspan") == ["2"]


def test_nested_block_content_is_raw_html() -> None:
    decision = classify_table(table("<table><tr><th>A</th></tr><tr><td><p>block</p></td></tr></table>"))
    assert decision.reason == "non-inline-safe-cell-content"


def test_simple_para_wrapper_is_unwrapped_only_in_safe_table() -> None:
    decision = classify_table(
        table(
            "<table><tr><th>A</th></tr><tr><td><span class='SimplePara'>hello <em>there</em></span></td></tr></table>"
        )
    )
    cell = decision.normalized_table.xpath(".//td")[0]
    assert decision.gfm_safe
    assert not cell.xpath(".//*[@class='SimplePara']")
    assert etree.tostring(cell, encoding="unicode") == "<td>hello <em>there</em></td>"


def test_caption_metadata_is_preserved_for_semantic_caption() -> None:
    decision = classify_table(
        table("<table><caption>Table 1: Values</caption><tr><th>A</th></tr><tr><td>1</td></tr></table>")
    )
    assert decision.caption is not None
    assert decision.caption.text == "Table 1: Values"
    assert decision.caption.source == "caption"
    assert decision.normalized_table.xpath("string(caption)") == "Table 1: Values"


def test_publisher_caption_wrapper_is_metadata() -> None:
    decision = classify_table(
        table(
            "<section><div class='Caption'>Table 2. Caption</div>"
            "<table><tr><th>A</th></tr><tr><td>1</td></tr></table></section>"
        ).xpath(".//table")[0]
    )
    assert decision.caption is not None
    assert decision.caption.source == "publisher-wrapper"
    assert decision.caption.text == "Table 2. Caption"


def test_normalization_is_deterministic_and_does_not_mutate_source() -> None:
    source = table("<table><tr><th>A</th></tr><tr><td><span class='SimplePara'>x</span></td></tr></table>")
    first = normalize_table(source)
    second = normalize_table(source)
    assert etree.tostring(first.normalized_table) == etree.tostring(second.normalized_table)
    assert source.xpath(".//*[@class='SimplePara']")
