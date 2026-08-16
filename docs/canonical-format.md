# Canonical format

Renderer-independent book directory. Not Astro-specific.

## Layout

- `book.json` — bibliographic metadata, ordered sections, assets, conversion tool version
- `toc.json` — navigation tree (`nav` preferred, else `ncx`, else inferred from spine)
- `conversion-report.json` — status, issues, stats
- `index.md` / `toc.md` — human entry points
- `content/*.md` — one file per Phase 1 reading unit
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
---
```

No prev/next/total. Sites derive those from `book.json`.

## Leafmd Markdown

UTF-8, YAML frontmatter, CommonMark + GFM tables, ATX headings, fenced code, raw HTML for explicit anchors / MathML / complex tables.

Internal EPUB ids are rewritten to namespaced explicit anchors:

```html
<a id="src-ch01-sec2"></a>
```

Do not rely on SSG heading slugs.

## Trust

The book directory is trusted relative to converter promises. A public HTML site must sanitize independently.
