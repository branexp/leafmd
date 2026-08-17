# leafmd

Compile EPUB 2/3 books into a **canonical Markdown book directory**.

`leafmd` is a private personal-library CLI. The EPUB stays the source of truth. Output is regenerated, not hand-edited. This is not a reading app and not a public upload service.

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

The format is renderer-independent. A future private site at `book.pettee.org` (Astro + Pagefind behind SWAG) can consume it later.

## Install

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Usage

```bash
leafmd convert BOOK.epub --output out/the-book
leafmd inspect BOOK.epub --json
leafmd validate out/the-book
leafmd report out/the-book
leafmd version
```

Exit codes: `0` ok or warnings, `1` completed with errors, `2` fatal or CLI usage error, `3` reserved for future application-level usage errors.

## Repo

Private GitHub: [`branexp/leafmd`](https://github.com/branexp/leafmd). Branch off `main` → PR → squash merge. See [docs/github-workflow.md](docs/github-workflow.md).

## Current behavior

The initial Phase 1 slice was one spine document per output file. Current `0.3.x` also includes:

- ingest guards (zip-slip, bomb limits, DRM), direct OPF/nav/NCX parsing, and an EbookLib cross-check
- evidence-ranked classification, conservative case-B merges, case-C fragment splits, virtual TOC parts, cover discovery, and text cleanup
- rewritten internal links and namespaced explicit HTML anchors, referenced raster images/SVG, and output validation
- conservative GFM tables and same-section local footnotes; complex tables and cross-document notes remain faithfully rewritten as raw HTML or links
- safe preservation of MathML, ruby, and bidi markup without MathML-to-LaTeX conversion

Still deferred: MOBI/PDF, DRM bypass, cache/incremental conversion, fonts/CSS/audio/video, optional Docker EPUBCheck (not currently a CLI option), and a website.

## License

[AGPL-3.0-or-later](LICENSE). v1 links [EbookLib](https://github.com/aerkalov/ebooklib), which is AGPL. This is an engineering precaution, not legal advice.

Converted book directories are your content. Do not commit copyrighted EPUBs to this repo.
