# Architecture

```text
EPUB ZIP
  → ingest guards
  → EbookLib adapter + OPF/nav/NCX parse
  → NormalizedPublication
  → SectionPlanner (Phase 1: one spine XHTML → one file)
  → rewrite links/assets
  → markdownify profile
  → BookDirectory writer
  → conversion-report.json
```

Nothing above `leafmd.parse.ebooklib_adapter` imports `ebooklib`. Public types live in `leafmd.model`.

EbookLib is a **cross-check only**. OPF, nav, and NCX truth come from the direct parsers.

Build plan and phase tickets: [implementation-plan.md](implementation-plan.md).
GitHub / PR workflow: [github-workflow.md](github-workflow.md).
