from leafmd.convert import convert_epub
from leafmd.report import new_report
from leafmd.transform.assets import sanitize_svg
from tests.fixtures.epub_builder import (
    HOSTILE_SVG,
    make_colliding_assets_book,
    make_epub2,
    make_epub3,
    make_hostile_svg_book,
    make_missing_image_book,
    make_remote_image_book,
    write_bytes,
)


def _codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def test_missing_image_reports_asset_missing(tmp_path) -> None:
    epub = write_bytes(tmp_path / "missing.epub", make_missing_image_book())
    _book_dir, report = convert_epub(epub, tmp_path / "out-missing")
    assert "ASSET_MISSING" in _codes(report)


def test_remote_image_is_not_fetched(tmp_path) -> None:
    epub = write_bytes(tmp_path / "remote.epub", make_remote_image_book())
    book_dir, report = convert_epub(epub, tmp_path / "out-remote")
    assert "ASSET_REMOTE" in _codes(report)
    assert list((book_dir / "assets" / "images").glob("*")) == []


def test_hostile_svg_is_sanitized(tmp_path) -> None:
    epub = write_bytes(tmp_path / "svg.epub", make_hostile_svg_book())
    book_dir, report = convert_epub(epub, tmp_path / "out-svg")
    assert "SVG_SANITIZED" in _codes(report)
    svg = (book_dir / "assets" / "images" / "evil.svg").read_text(encoding="utf-8")
    assert "<script" not in svg.lower()
    assert "onclick" not in svg.lower()
    assert "handler=" not in svg.lower()
    assert "javascript:" not in svg.lower()
    assert "https://evil.example" not in svg
    assert "foreignobject" not in svg.lower()


def test_sanitize_svg_unit() -> None:
    cleaned = sanitize_svg(HOSTILE_SVG, new_report(), "evil.svg").decode("utf-8")
    assert "<script" not in cleaned.lower()
    assert "onclick" not in cleaned.lower()
    assert "foreignobject" not in cleaned.lower()


def test_colliding_asset_names_are_disambiguated(tmp_path) -> None:
    epub = write_bytes(tmp_path / "collide.epub", make_colliding_assets_book())
    book_dir, _report = convert_epub(epub, tmp_path / "out-collide")
    names = sorted(path.name for path in (book_dir / "assets" / "images").glob("*.png"))
    assert names == ["pic-2.png", "pic.png"]


def test_epub2_meta_cover_and_epub3_cover_image(tmp_path) -> None:
    epub2 = write_bytes(tmp_path / "book2.epub", make_epub2())
    book2, _report2 = convert_epub(epub2, tmp_path / "out2")
    assert (book2 / "assets" / "images" / "cover.png").is_file()

    epub3 = write_bytes(tmp_path / "book3.epub", make_epub3())
    book3, _report3 = convert_epub(epub3, tmp_path / "out3")
    assert (book3 / "assets" / "images" / "cover.png").is_file()
    assert (book3 / "assets" / "images" / "pic.svg").is_file()
