from leafmd.model.publication import Resource
from leafmd.semantics.classify import classify_from_title


def test_classify_preface() -> None:
    resource = Resource(id="pref", href="preface.xhtml", media_type="application/xhtml+xml")
    semantic_type, evidence = classify_from_title("Preface", resource)
    assert semantic_type == "preface"
    assert evidence[0].source == "heading"


def test_classify_default_chapter() -> None:
    resource = Resource(id="x", href="x.xhtml", media_type="application/xhtml+xml")
    semantic_type, evidence = classify_from_title("Welcome", resource)
    assert semantic_type == "chapter"
    assert evidence[0].source == "spine"
