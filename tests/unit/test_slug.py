from leafmd.transform.slug import slugify


def test_slugify_basic() -> None:
    assert slugify("Chapter 1 Welcome") == "chapter-1-welcome"


def test_slugify_fallback() -> None:
    assert slugify("???") == "section"
