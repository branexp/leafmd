from leafmd.parse.hrefs import posix_join, posix_norm, split_fragment


def test_split_fragment() -> None:
    assert split_fragment("ch01.xhtml#p1") == ("ch01.xhtml", "p1")
    assert split_fragment("ch01.xhtml") == ("ch01.xhtml", None)


def test_posix_join_relative() -> None:
    assert posix_join("EPUB/ch01.xhtml", "images/pic.svg") == "EPUB/images/pic.svg"
    assert posix_join("EPUB/ch01.xhtml", "../nav.xhtml") == "nav.xhtml"
    assert posix_join("EPUB/ch01.xhtml", "#p1") == "EPUB/ch01.xhtml#p1"
    assert posix_join("EPUB/ch02.xhtml", "ch01.xhtml#p1") == "EPUB/ch01.xhtml#p1"


def test_posix_norm_strips_traversal() -> None:
    assert posix_norm("EPUB/../EPUB/ch01.xhtml") == "EPUB/ch01.xhtml"
    assert posix_norm("../evil") == "evil"
