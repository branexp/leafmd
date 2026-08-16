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
```

Exit codes: `0` ok, `1` completed with errors, `2` fatal, `3` usage.

## Repo

Private GitHub: [`branexp/leafmd`](https://github.com/branexp/leafmd). Branch off `main` → PR → squash merge. See [docs/github-workflow.md](docs/github-workflow.md).

## Phase 1 scope

Well-formed EPUB 2/3, mostly one XHTML document per file:

- ingest guards (zip-slip, bombs, DRM)
- EbookLib adapter + our OPF / nav / NCX parse
- spine-ordered Markdown via markdownify
- referenced raster images + SVG
- rewritten internal links and explicit HTML anchors
- `inspect` / `validate`

Not in v1: MOBI/PDF, DRM, cache, incremental convert, semantic split/merge beyond spine+nav titles, fonts/CSS/AV, a website.

## License

[AGPL-3.0-or-later](LICENSE). v1 links [EbookLib](https://github.com/aerkalov/ebooklib), which is AGPL. This is an engineering precaution, not legal advice.

Converted book directories are your content. Do not commit copyrighted EPUBs to this repo.
