from collections.abc import Mapping
from pathlib import Path

from leafmd.convert import convert_epub
from leafmd.model.images import ImageAnalysis, ImageBlock, ImageBlockKind, ImageDecision
from tests.fixtures.epub_builder import MIN_PNG, make_custom_epub3, write_bytes


class StaticImageAnalyzer:
    backend = "static-test"

    def analyze_batch(self, images: Mapping[str, Path]) -> dict[str, ImageAnalysis]:
        return {
            href: ImageAnalysis(
                source_href=href,
                decision=ImageDecision.REPLACE,
                blocks=(ImageBlock(ImageBlockKind.TEXT, "Recovered from image", "text"),),
                labels=("text",),
                reason="markdown-representable",
                backend=self.backend,
            )
            for href in images
        }


class FailingImageAnalyzer:
    backend = "failing-test"

    def analyze_batch(self, images: Mapping[str, Path]) -> dict[str, ImageAnalysis]:
        raise RuntimeError("test failure")


def test_convert_epub_can_replace_raster_content_without_dropping_original_asset(tmp_path) -> None:
    epub = make_custom_epub3(
        title="OCR Fixture",
        chapters=[("ch01", "ch01.xhtml", '<h1>Chapter</h1><p><img src="images/scan.png" alt="scan"/></p>')],
        extras={"EPUB/images/scan.png": MIN_PNG},
        manifest_extra='    <item id="scan" href="images/scan.png" media-type="image/png"/>\n',
    )
    source = write_bytes(tmp_path / "ocr.epub", epub)
    book_dir, report = convert_epub(source, tmp_path / "out", image_analyzer=StaticImageAnalyzer())
    markdown = next((book_dir / "content").glob("*.md")).read_text(encoding="utf-8")
    assert "Recovered from image" in markdown
    assert "scan.png" not in markdown
    assert (book_dir / "assets" / "images" / "scan.png").is_file()
    assert report.stats.images_analyzed == 1
    assert report.stats.image_replacements == 1


def test_analyzer_failure_keeps_original_image_and_completes_with_warning(tmp_path) -> None:
    epub = make_custom_epub3(
        title="OCR Failure Fixture",
        chapters=[("ch01", "ch01.xhtml", '<h1>Chapter</h1><p><img src="images/scan.png"/></p>')],
        extras={"EPUB/images/scan.png": MIN_PNG},
        manifest_extra='    <item id="scan" href="images/scan.png" media-type="image/png"/>\n',
    )
    source = write_bytes(tmp_path / "ocr-failure.epub", epub)
    book_dir, report = convert_epub(source, tmp_path / "out", image_analyzer=FailingImageAnalyzer())
    markdown = next((book_dir / "content").glob("*.md")).read_text(encoding="utf-8")

    assert "../assets/images/scan.png" in markdown
    assert (book_dir / "assets" / "images" / "scan.png").is_file()
    assert report.status == "completed_with_warnings"
    assert any(issue.code == "IMAGE_ANALYSIS_FAILED" for issue in report.issues)
    assert report.stats.image_analysis_failures == 1
