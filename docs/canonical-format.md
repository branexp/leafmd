# Canonical format

Renderer-independent book directory. Not Astro-specific.

## Layout

- `book.json` — schema-v1 bibliographic metadata, planned sections, assets, and conversion tool version
- `toc.json` — schema-v1 navigation tree formed from EPUB nav ∪ NCX; nav labels/order win on matching targets, then inferred spine entries are used only when neither source is usable
- `conversion-report.json` — status, issues, stats
- `index.md` / `toc.md` — human entry points
- `content/*.md` — one file per planned reading section; Phase 3 may merge or split source documents
- `assets/images/` — referenced raster + SVG

## Frontmatter

```yaml
---
id: sec-005
title: "The Beginning"
type: chapter
order: 5
source:
  - href: EPUB/ch01.xhtml
    fragment: welcome
---
```

No prev/next/total. Sites derive those from `book.json`. Current section records include `id`, `order`, `type`, `title`, `path`, `role`, `toc_path`, and `sources`; `confidence` and source `fragment` values are optional where applicable.

## Leafmd Markdown

UTF-8, YAML frontmatter, CommonMark + GFM tables, ATX headings, fenced code, and raw HTML for explicit anchors, MathML, ruby/bidi markup, and complex tables. Simple same-section notes use GFM footnotes; cross-document or ambiguous notes remain rewritten links and anchors. Unsafe active elements and URL schemes are removed by the converter's rewrite boundary.

Internal EPUB ids are rewritten to namespaced explicit anchors:

```html
<a id="src-ch01-sec2"></a>
```

Do not rely on SSG heading slugs.

## Manifest and validation

`book.json` and `toc.json` retain `schema_version: 1`; `conversion-report.json` retains its existing `status`, `tool_version`, `source_validation`, `issues`, and `stats` keys. Phase 4 adds no footnote manifest or new index file. The validator requires the five index files, checks section ids/paths and assets, verifies relative links and explicit anchors, validates TOC paths/fragments, and rejects missing or duplicate GFM footnote definitions with codes such as `VALIDATE_FOOTNOTE_MISSING` and `VALIDATE_FOOTNOTE_DUPLICATE`.

## Trust

The book directory is trusted relative to converter promises. A public HTML site must sanitize independently.
