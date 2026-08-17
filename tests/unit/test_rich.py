from lxml import etree

from leafmd.transform.rich import (
    contains_rich_markup,
    is_text_normalization_protected,
    preserve_rich_markup,
    protected_rich_nodes,
    sanitize_rich_tree,
)


def _tree(markup: str) -> etree._Element:
    return etree.fromstring(markup.encode(), parser=etree.XMLParser(resolve_entities=False))


def test_mathml_structure_and_meaningful_attributes_are_preserved() -> None:
    root = _tree(
        '<p>before<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">'
        "<mrow><mi>x</mi><mo>=</mo><msup><mi>y</mi><mn>2</mn></msup></mrow>"
        "</math>after</p>"
    )
    sanitize_rich_tree(root)
    math = next(node for node in root.iter() if node.tag.endswith("}math"))
    assert math.get("display") == "block"
    assert [node.tag.rsplit("}", 1)[-1] for node in math.iter()] == [
        "math",
        "mrow",
        "mi",
        "mo",
        "msup",
        "mi",
        "mn",
    ]
    assert "x" in "".join(math.itertext())


def test_ruby_and_bidi_markup_and_safe_direction_survive() -> None:
    root = _tree(
        "<p><ruby><rb>漢字</rb><rt>かんじ</rt><rp>(</rp><rp>)</rp></ruby>"
        '<bdi dir="rtl">שלום</bdi><bdo dir="ltr">abc</bdo></p>'
    )
    sanitize_rich_tree(root)
    assert [node.tag for node in root.iter()] == ["p", "ruby", "rb", "rt", "rp", "rp", "bdi", "bdo"]
    assert root.find("bdi").get("dir") == "rtl"  # type: ignore[union-attr]
    assert root.find("bdo").get("dir") == "ltr"  # type: ignore[union-attr]
    assert "漢字" in "".join(root.itertext()) and "かんじ" in "".join(root.itertext())


def test_invalid_direction_is_removed_without_reordering_text() -> None:
    root = _tree("<p>א< bdi />x</p>".replace("< bdi", "<bdi"))
    root[0].set("dir", "sideways")
    root[0].text = "א\u200fx"
    sanitize_rich_tree(root)
    assert root[0].get("dir") is None
    assert root[0].text == "א\u200fx"


def test_rich_text_is_protected_from_normalization_and_copy_isolated() -> None:
    root = _tree("<p>outside<ruby><rb>A-</rb><rt>え</rt></ruby><math><mi>x-</mi></math></p>")
    nodes = protected_rich_nodes(root)
    assert contains_rich_markup(root)
    assert all(is_text_normalization_protected(node) for node in nodes)
    assert root not in nodes
    copied = preserve_rich_markup(root)
    assert copied is not root
    copied.find("ruby/rb").text = "changed"  # type: ignore[union-attr]
    assert root.find("ruby/rb").text == "A-"  # type: ignore[union-attr]


def test_active_elements_event_attributes_and_unsafe_urls_are_removed() -> None:
    root = _tree(
        '<div onclick="alert(1)"><math onload="x"><mi>x</mi></math>'
        '<a href="javascript:alert(1)" onmouseover="x">bad</a>'
        '<img src="data:text/html,%3Cscript%3Ex%3C/script%3E" /><a href="https://example.test">ok</a>'
        '<script>alert(1)</script><iframe src="https://evil.test">frame</iframe></div>'
    )
    sanitize_rich_tree(root)
    output = etree.tostring(root, encoding="unicode")
    assert "script" not in output.lower()
    assert "iframe" not in output.lower()
    assert "onclick" not in output and "onload" not in output and "onmouseover" not in output
    assert "javascript:" not in output and "data:text/html" not in output
    assert 'href="https://example.test"' in output


def test_relative_and_mailto_urls_are_safe() -> None:
    root = _tree('<p><a href="../chapter.xhtml#x">relative</a><a href="mailto:a@example.test">mail</a></p>')
    sanitize_rich_tree(root)
    assert root[0].get("href") == "../chapter.xhtml#x"
    assert root[1].get("href") == "mailto:a@example.test"
