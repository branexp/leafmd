# Optional image-to-Markdown recovery

`leafmd convert --convert-images` can analyze referenced raster images with an external PaddleOCR PP-StructureV3 installation. PaddleOCR is intentionally **not** a leafmd Python dependency: keep it in a separate environment and put its `paddleocr` executable on `PATH`.

The feature is conservative. JPEG, PNG, and WebP assets are eligible; covers, SVG, GIF, remote images, and unsupported media are preserved. PP-StructureV3 runs once for the eligible image batch in a book with table and formula recognition enabled and chart parsing disabled.

Leafmd consumes PP-StructureV3's structured JSON rather than its final Markdown. Text-only images are reconstructed as prose, recognized tables are sanitized into an lxml `<table>` and then pass through leafmd's existing GFM/raw-HTML table policy, and recognized equations become LaTeX math. If the analyzer sees a figure, image, chart, seal, or an unknown layout type, leafmd preserves the original image.

Context can override an otherwise convertible result. A formula may replace an inline image, but block text/tables are not inserted into mixed inline prose. Publisher `figcaption` text wins over OCR-generated caption blocks.

Original image assets are always copied into `assets/images/`, even when an occurrence is replaced in Markdown. Analyzer failures after startup are warnings and preserve the source images. If `--convert-images` is explicitly requested but `paddleocr` is not on `PATH`, leafmd reports a usage error.

Image analysis adds these conversion-report statistics:

- `images_analyzed`
- `image_replacements`
- `image_analysis_failures`

Relevant issue codes include `IMAGE_ANALYSIS_CANDIDATE`, `IMAGE_CONVERTED`, `IMAGE_PRESERVED`, `IMAGE_PRESERVED_CONTEXT`, `IMAGE_ANALYSIS_MISSING`, `IMAGE_ANALYSIS_FAILED`, and `IMAGE_CONVERSION_UNSAFE`.
