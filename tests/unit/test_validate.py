import json
from pathlib import Path

from leafmd.convert import convert_epub
from leafmd.model.issues import IssueSeverity
from leafmd.validate.output import validate_book_directory
from tests.fixtures.epub_builder import make_epub3, make_fragment_book, write_bytes


def _codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def test_validate_accepts_generated_book(tmp_path: Path) -> None:
    epub = write_bytes(tmp_path / "ok.epub", make_fragment_book())
    book_dir, _report = convert_epub(epub, tmp_path / "out-ok")
    validation = validate_book_directory(book_dir)
    assert not validation.has_errors()
    assert not validation.has_fatal()


def test_validate_reports_missing_schema_fields(tmp_path: Path) -> None:
    epub = write_bytes(tmp_path / "book.epub", make_epub3())
    book_dir, _report = convert_epub(epub, tmp_path / "out-schema")
    book_path = book_dir / "book.json"
    payload = json.loads(book_path.read_text(encoding="utf-8"))
    del payload["title"]
    payload["sections"][0]["path"] = payload["sections"][0]["path"]
    payload["sections"].append(dict(payload["sections"][0]))
    book_path.write_text(json.dumps(payload), encoding="utf-8")
    validation = validate_book_directory(book_dir)
    assert "VALIDATE_SCHEMA" in _codes(validation)
    assert "VALIDATE_DUP_PATH" in _codes(validation)
    assert "VALIDATE_DUP_SECTION" in _codes(validation)


def test_validate_reports_missing_toc_fragment(tmp_path: Path) -> None:
    epub = write_bytes(tmp_path / "book.epub", make_fragment_book())
    book_dir, _report = convert_epub(epub, tmp_path / "out-toc")
    toc_path = book_dir / "toc.json"
    payload = json.loads(toc_path.read_text(encoding="utf-8"))
    payload["nodes"][0]["href"] = f"{payload['nodes'][0]['href'].split('#', 1)[0]}#missing-anchor"
    toc_path.write_text(json.dumps(payload), encoding="utf-8")
    validation = validate_book_directory(book_dir)
    assert "VALIDATE_TOC_ANCHOR_MISSING" in _codes(validation)


def test_strict_promotes_unresolved_link(tmp_path: Path) -> None:
    from tests.fixtures.epub_builder import make_epub3 as broken

    epub = write_bytes(tmp_path / "broken.epub", broken(broken_link=True))
    _book_dir, report = convert_epub(epub, tmp_path / "out-strict", strict=True)
    unresolved = next(issue for issue in report.issues if issue.code == "LINK_UNRESOLVED")
    assert unresolved.severity is IssueSeverity.ERROR
    assert report.status == "completed_with_errors"


def test_conversion_report_has_required_stats(tmp_path: Path) -> None:
    epub = write_bytes(tmp_path / "book.epub", make_epub3())
    book_dir, _report = convert_epub(epub, tmp_path / "out-report")
    payload = json.loads((book_dir / "conversion-report.json").read_text(encoding="utf-8"))
    assert set(payload) >= {"status", "tool_version", "source_validation", "issues", "stats"}
    assert set(payload["stats"]) >= {
        "source_documents",
        "generated_files",
        "images_copied",
        "unresolved_links",
        "assets_skipped",
    }
    validation = validate_book_directory(book_dir)
    assert "VALIDATE_SCHEMA" not in _codes(validation)
