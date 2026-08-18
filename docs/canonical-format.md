# Canonical format

Renderer-independent book directory. It is not tied to Astro, MDX, or a specific reading application.

## Layout

- `book.json` — schema-v1 bibliographic metadata, planned sections, copied assets, and conversion tool version
- `toc.json` — schema-v1 navigation tree formed from EPUB nav ∪ NCX; nav labels/order win on matching targets, with inferred planned sections used when usable navigation is absent
- `conversion-report.json` — conversion status, source-validation namespace, issues, and stats
- `index.md` / `toc.md` — human entry points
- `content/*.md` — one file per planned reading section; planning may merge consecutive source documents or split fragment-targeted sections
- `assets/images/` — referenced JPEG/PNG/GIF/WebP/SVG assets plus the discovered cover

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

No prev/next/total fields are stored. Consumers derive navigation from `book.json`/`toc.json`. Section records include `id`, `order`, `type`, `title`, `path`, `role`, `toc_path`, `sources`, and `confidence`; source `fragment` values are optional where applicable.

## Leafmd Markdown

UTF-8, YAML frontmatter, CommonMark-compatible Markdown with GFM tables/footnotes, ATX headings, fenced code, and raw HTML where Markdown would lose semantics. Raw HTML is used for explicit compatibility anchors, source MathML, ruby/bidi markup, and complex tables.

Ordinary source line wrapping inside a paragraph is normalized to spaces; adjacent block paragraphs remain separate, and explicit `<br>` elements remain hard breaks. Recognizable double-decoding sequences such as `Ã©` and `Â ` are repaired conservatively while legitimate Unicode is preserved. Simple same-section notes use deterministic GFM footnotes; cross-document or ambiguous notes remain rewritten links/anchors. Safe rectangular tables can become GFM; spanning, nested, ambiguous, or otherwise rich tables remain rewritten raw HTML. Unsafe active elements, unsafe URL schemes, and unsafe rich-content attributes are removed at the converter boundaries.

Internal EPUB ids are rewritten to namespaced explicit anchors:

```html
<a id="src-ch01-sec2"></a>
```

These empty, zero-width anchors are part of the canonical compatibility contract because content links and TOC fragments target them. Consumers must not rely on generated heading slugs instead.

## Optional image-derived content

When `convert --convert-images` is enabled, eligible copied raster assets may also be analyzed. A safe text/table/formula result can replace an `<img>` occurrence in `content/*.md`; visual, ambiguous, unsupported, or context-incompatible results keep the original image reference. Original assets remain listed in `book.json.assets` and remain present under `assets/images/` even when an occurrence is replaced.

Recognized raster formulas are emitted as LaTeX (`$...$` inline or `$$...$$` block). This does **not** change the source-MathML contract: MathML present in the EPUB remains sanitized raw HTML rather than being converted to LaTeX.

## Report and validation

`book.json` and `toc.json` use `schema_version: 1`. `conversion-report.json` has the top-level keys `status`, `tool_version`, `source_validation`, `issues`, and `stats`. Base stats are `source_documents`, `generated_files`, `images_copied`, `unresolved_links`, and `assets_skipped`. When image analysis is enabled, the report additionally includes `images_analyzed`, `image_replacements`, and `image_analysis_failures`.

`leafmd validate BOOKDIR` independently re-reads the generated directory. It requires the five top-level index/report files, checks manifest fields and section/assets paths, verifies relative links and explicit anchors, validates TOC paths/fragments, detects path escapes, and rejects missing or duplicate GFM footnote definitions. Validation does not run automatically as part of `convert` and does not rewrite the stored conversion report.

## Trust

The canonical directory is trusted only relative to leafmd's converter promises. It is not a public-HTML security boundary; any public renderer must apply its own sanitization policy.
