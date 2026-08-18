# Architecture

## Conversion pipeline

```text
EPUB ZIP
  → archive inspection (ZIP validity, DRM policy, mimetype diagnostics)
  → direct container/OPF/nav/NCX parse + EbookLib cross-check
  → NormalizedPublication
  → SectionPlanner (case A default; conservative merges/splits + virtual TOC parts)
  → copy referenced assets and cover
  → optional raster analysis (`ImageAnalyzer` / PaddleOCR CLI adapter)
  → build TargetMap
  → for each planned source: parse → slice → optional image replacement → rewrite links/assets/active content
  → merge planned roots
  → normalize/render tables, notes, source MathML, ruby, bidi, and text
  → BookDirectory writer
  → conversion-report.json
```

`leafmd validate BOOKDIR` is a **separate** pass. `convert` does not invoke `OutputValidator` automatically.

## Boundaries

Nothing above `leafmd.parse.ebooklib_adapter` imports `ebooklib`. Public IR and orchestration use `leafmd.model` types; parsing and rendering transforms may operate on lxml trees at their documented boundaries. EbookLib objects never cross the adapter boundary, and direct OPF/nav/NCX parsing remains authoritative.

`TargetMap` is built before source-tree rewriting/rendering and is the single source of truth for generated anchors and rewritten internal destinations. Rich-content and image transforms do not invent output paths or anchor ids.

Asset collection happens before image analysis so optional analyzers only receive already-copied, local raster files. `leafmd.images.ImageAnalyzer` is a small protocol boundary; the built-in `PaddleCliAnalyzer` invokes an external `paddleocr` executable and intentionally does not make PaddleOCR a leafmd Python dependency. Analysis happens once per eligible source image; replacement happens per `<img>` occurrence before normal link/asset rewriting. Original copied assets remain in the canonical directory even when an occurrence is replaced with semantic content.

Rich-content handling is conservative. Source MathML, ruby, and bidi markup are preserved as sanitized raw HTML; simple local notes and safe tables can become GFM. Optional image recovery is distinct: a formula recognized from a raster image is emitted as LaTeX because it is analyzer output, not source MathML conversion.

## Key modules

```text
src/leafmd/
  cli.py                  # Typer/Rich commands and exit codes
  convert.py              # thin top-level orchestration
  ingest/archive.py       # ZIP/DRM/mimetype policy
  parse/                  # package, navigation, safe XML/HTML recovery, EbookLib cross-check
  semantics/              # classification and section planning
  images/                 # optional analyzer protocol, Paddle CLI adapter, image replacement
  transform/              # links, assets, slicing/merging, tables, notes, rich safety, text normalization
  render/                 # Markdown rendering and canonical-directory writing
  validate/output.py      # independent generated-directory validation
```

Current roadmap/history: [implementation-plan.md](implementation-plan.md). Repository workflow: [github-workflow.md](github-workflow.md).
