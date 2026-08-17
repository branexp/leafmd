# Architecture

```text
EPUB ZIP
  → ingest guards
  → EbookLib adapter + OPF/nav/NCX parse
  → NormalizedPublication
  → SectionPlanner (case A default; conservative case-B merges, case-C splits, virtual TOC parts)
  → TargetMap + asset collection
  → slice each planned source section
  → rewrite links/assets/active content per source
  → merge planned roots
  → rich-content classification/normalization
  → markdownify profile + raw HTML preservation
  → BookDirectory writer
  → OutputValidator
  → conversion-report.json
```

Nothing above `leafmd.parse.ebooklib_adapter` imports `ebooklib`. Public IR and orchestration use `leafmd.model` types; parsing and rendering transforms may operate on lxml trees at their documented boundaries. EbookLib objects never cross the adapter boundary.

`TargetMap` is built before rendering and remains the single source of truth for generated anchors and rewritten destinations. Rich-content transforms do not invent output paths or anchor ids.

EbookLib is a **cross-check only**. OPF, nav, and NCX truth come from the direct parsers.

Build plan and phase tickets: [implementation-plan.md](implementation-plan.md).
GitHub / PR workflow: [github-workflow.md](github-workflow.md).
