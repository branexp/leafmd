# leafmd

Compile EPUB 2/3 books into a **canonical Markdown book directory**.

`leafmd` is a local CLI for reconstructing useful Markdown from EPUB packages. The EPUB remains the source of truth: generated book directories are regenerate-only output, not an editing format. The repository is public, but the converter is designed for local/personal-library workflows rather than as an upload service.

## What you get

```text
<book-slug>/
  index.md
  toc.md
  book.json
  toc.json
  conversion-report.json
  content/
    001-title-page.md
    005-chapter-01-the-beginning.md
  assets/
    images/
```

The format is renderer-independent; a separate reading site or other consumer can use the generated directory without leafmd depending on a specific SSG.

## Install

Python 3.11+ is supported. The repository's default development interpreter is Python 3.12.

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

For development tools:

```bash
uv pip install -e ".[dev]"
```

## Usage

```bash
leafmd convert BOOK.epub --output out/the-book
leafmd convert BOOK.epub --output out/the-book --convert-images
leafmd inspect BOOK.epub --json
leafmd validate out/the-book
leafmd report out/the-book
leafmd version
```

If `--output` is omitted, `convert` writes to a slug derived from the book title. `--strict` promotes selected conversion warnings (`LINK_UNRESOLVED`, `ASSET_MISSING`, and `RENDER_MISSING_SOURCE`) to errors.

Exit codes:

- `0` — success or warnings only
- `1` — conversion/validation completed with errors
- `2` — fatal conversion failure or CLI parser/usage error
- `3` — application usage/configuration error, currently used when an explicitly requested optional analyzer is unavailable

`convert` writes the canonical directory and `conversion-report.json`; it does **not** automatically run the output validator. Use `leafmd validate BOOKDIR` as a separate integrity check.

## Optional image recovery

`--convert-images` enables conservative semantic recovery from referenced raster images using an external PaddleOCR PP-StructureV3 installation. PaddleOCR is intentionally not a leafmd dependency: install it separately and ensure a compatible `paddleocr` executable is on `PATH`.

JPEG, PNG, and WebP assets are eligible for analysis; covers, GIF, SVG, remote images, and unsupported media are preserved. Text-only results can become prose, recognized tables are sanitized and passed through leafmd's normal table policy, and recognized formula images become LaTeX math. Images containing figures/charts or unsupported/ambiguous layout types remain images. Block content is not injected into mixed inline prose; an inline formula is the only inline replacement.

Original image assets are still copied to `assets/images/` even when an occurrence is replaced in Markdown. Analyzer failures after startup are warnings and preserve the source image. If `--convert-images` is requested but `paddleocr` is not available, conversion exits with code `3`.

The external PaddleOCR process is a separate dependency/trust boundary. Leafmd itself does not download EPUB resources or model files; depending on how PaddleOCR is installed and provisioned, Paddle may manage model downloads or caches outside leafmd's control.

## Current behavior

Current `main` includes:

- ZIP/EPUB inspection, DRM rejection, mimetype diagnostics, direct container/OPF/nav/NCX parsing, and an EbookLib cross-check
- evidence-ranked semantic classification, conservative multi-file merges and fragment-based splits, virtual TOC parts, cover discovery, and text cleanup
- a global target map for rewritten internal links and namespaced explicit HTML anchors
- referenced JPEG/PNG/GIF/WebP/SVG assets and covers, with remote assets never fetched
- conservative GFM tables and same-section local footnotes; complex tables and cross-document notes remain rewritten raw HTML or links
- safe preservation of source MathML, ruby, and bidi markup
- optional PaddleOCR-backed raster-to-text/table/formula recovery via `--convert-images`
- an independent `validate` command for generated-directory schema, link, anchor, TOC, asset, and GFM-footnote checks

Not implemented: recursive/batch conversion, EPUBCheck integration, html5lib runtime recovery, parse-based SVG sanitization, cache/incremental conversion, MOBI/PDF input, DRM bypass, fonts/CSS/audio/video reconstruction, or a reading website.

## Development and repository workflow

GitHub: [`branexp/leafmd`](https://github.com/branexp/leafmd). Use focused branches and PRs into `main`; CI runs ruff, mypy, and pytest on Python 3.11 and 3.12. See [docs/github-workflow.md](docs/github-workflow.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[AGPL-3.0-or-later](LICENSE). leafmd links [EbookLib](https://github.com/aerkalov/ebooklib), which is AGPL. This is an engineering precaution, not legal advice.

Converted book directories are your content. Do not commit copyrighted EPUBs or converted personal-library trees to this repository.
