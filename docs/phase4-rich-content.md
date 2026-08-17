# Phase 4 — Rich-content reconstruction

**Status:** implemented and acceptance-tested locally on `feat/phase4-rich-content`; not pushed or merged
**Baseline:** `main` / `a6dee61` (`0.2.0`)  
**Scope:** tables, notes, MathML preservation, ruby, and bidi-aware rendering  
**Source of truth:** synthetic fixtures plus characterization of the three local EPUBs in `tmp-convert/`

This phase improves semantic fidelity without changing the canonical book-directory schema or the existing explicit-anchor contract. It is deliberately conservative: a construct is converted to Markdown only when the conversion is demonstrably lossless; otherwise its rewritten raw HTML is retained.

## 1. Corpus evidence

The uploaded EPUBs are probes, not fixtures. They are not committed or copied into test data.

| Probe | Relevant structure | Current converter result | Phase 4 implication |
|---|---|---|---|
| Energy Storage | 27 XHTML spine files; 66 HTML tables; 65 tables with `thead`; one frontmatter table with `rowspan`/`colspan`; class-based `.Caption`/`.Table`; 368 block and 31 inline equation-image containers; no MathML, notes, ruby, or bidi | Conversion and validation succeed; tables remain raw HTML; equation images are retained | Convert safe rectangular tables; preserve the spanning frontmatter table; keep raster equations and captions intact |
| Stochastic Processes and Calculus | 22 XHTML files; one 3×7 table with `colgroup` and nested `.SimplePara`; 14 footnote sections / 81 footnotes; 45 captions; 1,619 block and 1,068 inline equation-image containers; no MathML, ruby, or bidi | Conversion and validation succeed; the table remains raw HTML; footnotes retain publisher HTML; equation images are retained | Add a local-footnote path, test nested table wrappers, and keep equation-image semantics unchanged |
| How Economics Explains the World | 27 XHTML files; no HTML tables or MathML; 283 note-like cross-document links to `Notes.xhtml`; 49 images; publisher-specific paired source/return anchors | Conversion and validation succeed; note links remain ordinary rewritten links | Do not force cross-document notes into local GFM footnotes; preserve the source/return relationship |

The probes establish that a green validation report does not prove rich-content fidelity. Validation must continue to check paths, links, and anchors; Phase 4 tests additionally check content semantics.

## 2. Goals and non-goals

### Goals

1. Classify tables before rendering and convert only safe rectangular tables to GFM.
2. Preserve complex tables, captions, and cell content without loss.
3. Recognize standard EPUB note metadata and conservative publisher-specific note patterns.
4. Convert only simple, local, unambiguous notes to deterministic GFM footnotes.
5. Preserve complex or cross-document notes as rewritten links/HTML with anchors intact.
6. Preserve MathML as raw HTML; preserve ruby markup and bidi directionality.
7. Keep unsafe active elements and URL schemes out of emitted rich HTML using the existing rewrite/security boundary.
8. Add synthetic coverage for features absent from the three real probes.

### Non-goals

- No MathML-to-LaTeX conversion.
- No html5lib runtime fallback; that remains Phase 5 characterization work.
- No colspan/rowspan flattening.
- No new `book.json`/`toc.json` schema version or footnote manifest.
- No CSS/font/layout reconstruction, JavaScript, media overlays, or website sanitizer.
- No copyrighted EPUBs in git and no network fetches during conversion.

## 3. Architecture

### Pipeline placement

Rich-content handling runs after section slicing/merging and link/asset rewriting, but before Markdown rendering:

```text
parse → plan/slice/merge → build TargetMap/assets
     → rewrite links/assets/active content
     → classify/normalize tables and notes
     → render Markdown + raw HTML
     → write canonical directory → validate
```

`TargetMap` remains authoritative. Rich-content transforms may preserve or remove a source node, but they must not invent output anchor IDs or independently rewrite internal destinations.

### Module boundaries

```text
src/leafmd/transform/tables.py   # table classification and safe normalization
src/leafmd/transform/notes.py    # note reference/definition analysis
src/leafmd/transform/rich.py     # MathML/ruby/bidi preservation and safety predicates
src/leafmd/render/markdown.py    # renderer integration only
```

The transform modules operate on lxml trees and small typed records. They do not know output paths, write files, or mutate manifests. `render/markdown.py` owns final Markdown/raw-HTML emission. `writer.py` remains filesystem orchestration.

## 4. Frozen decisions / ADRs

### ADR-04-1 — Keep the canonical model stable

**Decision:** retain `schema_version: 1`, the current five index files, flat `content/`, and namespaced `src-*` anchors. Notes are represented in content, not a new manifest database.

**Trade-off:** consumers do not get a structured footnote index, but output remains compatible with the planned reading site and existing validators.

### ADR-04-2 — Conservative Markdown, faithful fallback

**Decision:** use GFM only for proven-safe tables and simple local notes. Preserve rewritten raw HTML for complex tables, cross-document notes, MathML, ruby, and other constructs with no faithful Markdown equivalent.

**Trade-off:** some output is less aesthetically uniform, but silent data loss is worse than raw HTML in a trusted book directory.

### ADR-04-3 — No source-anchor ownership changes

**Decision:** build the global target map before rich-content transforms. Preserve the existing explicit anchor injection and link rewriting rules.

**Trade-off:** a rich transform cannot optimize an anchor layout locally, but cross-file links and TOC targets remain reliable.

### ADR-04-4 — No claims beyond converter trust

**Decision:** reuse `rewrite_tree` security behavior and extend it only for rich-content hazards. The generated directory is not declared safe public HTML; a future site sanitizer remains required.

## 5. Content contracts

### 5.1 Tables

A table is **GFM-safe** only when all of these hold:

- every row has the same number of cells after accounting for the source grid;
- no `rowspan` or `colspan` is present;
- a header row is explicit (`thead` or `th`) or the fixture contract explicitly permits a first-row header;
- cells contain only inline-safe content after removing known publisher wrappers such as `.SimplePara`;
- no nested table, list, block quote, preformatted block, image requiring special handling, MathML, or ruby occurs in a cell;
- caption text can be emitted without being lost or duplicated.

Safe tables are normalized only enough to remove known harmless wrappers, then rendered as GFM. A table with spans, ambiguous headers, block content, or rich content that markdownify could damage remains raw HTML after link/asset rewriting.

Caption policy:

- preserve every caption;
- for a GFM-safe table, emit the caption as one deterministic Markdown paragraph immediately before the table (including its number when present);
- if the caption cannot be represented faithfully as inline Markdown, keep the complete table, including `<caption>` or publisher-equivalent caption markup, as raw HTML;
- never silently discard or duplicate captions.

The Springer-like class forms observed in the probes (`.Table`, `.Caption`, `.CaptionNumber`, `.CaptionContent`, `.Figure`, `.Equation`) are fixture targets, not special permission to discard generic semantic HTML.

### 5.2 Notes

Recognize, in descending confidence:

1. `epub:type="noteref"` / `role="doc-noteref"` references and `epub:type="footnote"` / `role="doc-footnote"` definitions;
2. explicit same-document or cross-document target-map relationships;
3. conservative publisher patterns such as a superscript reference paired with a definition anchor and a return link.

A note is **simple/local** only when it has exactly one definition, one unambiguous reference relationship, ordinary inline content, no nested note/table/math/ruby/block content, and both reference and definition belong to the same generated Markdown section. Labels are deterministic and based on source identity, not encounter order alone.

Simple/local notes become GFM footnotes:

```markdown
Text with a note[^note-1].

[^note-1]: Inline note text.
```

The exact label sanitizer and numbering are owned by the notes ticket and must be deterministic across repeated conversions. Complex, ambiguous, or cross-section/cross-document notes remain ordinary rewritten links and explicit anchors (or raw HTML where required). In particular, the Economics probe's `Notes.xhtml` relationships must not be collapsed into a local footnote that loses navigation back to the source.

### 5.3 MathML

- Preserve MathML as raw HTML, including namespace and meaningful mathematical attributes.
- Do not convert to LaTeX or plain text.
- Rich transforms must not run text normalization inside MathML.
- Strip scripts, event attributes, unsafe URL-bearing attributes, and active foreign content according to the existing security policy; preserve mathematical structure where safe.
- Add synthetic fixtures because none of the three probes contain MathML.

Raster equation images in the probes are ordinary assets and remain ordinary images. Their `alt` text and source anchors must survive.

### 5.4 Ruby and bidi

- Preserve `<ruby>`, `<rb>`, `<rt>`, and `<rp>` as raw HTML; do not turn pronunciation into parenthetical prose.
- Preserve Unicode directional marks and safe `dir="rtl|ltr|auto"`, `<bdi>`, and `<bdo>` attributes.
- Do not reorder text or apply whitespace/hyphen normalization inside bidi-sensitive or ruby nodes.
- Add synthetic fixtures because the three probes contain neither feature.

## 6. Ticket decomposition

Tickets are intentionally non-overlapping. Each coding subagent receives an isolated worktree and must commit only its ticket. The parent reviews and integrates in dependency order.

### P4-0 — Contract and fixture specification (parent)

**Writes:** this document and the implementation-plan scoreboard.  
**Done when:** contracts above are accepted; no schema, LaTeX, html5lib, or website scope leaks into tickets.

### P4-1 — Synthetic rich-content fixtures

**Writes:** `tests/fixtures/epub_builder.py`, `tests/integration/test_rich_content_fixtures.py`.  
**Must add:** safe rectangular/captioned table; rowspan/colspan table; nested/block table; standard local note; complex note; cross-document note; MathML; ruby; RTL/mixed bidi; Springer-like caption/table/equation wrappers.  
**Must not write:** production transform or renderer code.  
**Verification:** each fixture has a focused invariant and validates the generated directory.

### P4-2 — Table classifier/normalizer

**Writes:** `src/leafmd/transform/tables.py`, `tests/unit/test_tables.py`.  
**API:** typed decision/result for GFM-safe versus raw HTML, with caption metadata and a reason for preservation.  
**Must not write:** `render/markdown.py`, `writer.py`, notes code, or report schema.  
**Verification:** unit tests cover rectangular headers, spans, nested blocks, wrapper unwrapping, captions, and determinism.

### P4-3 — Note classifier/normalizer

**Writes:** `src/leafmd/transform/notes.py`, `tests/unit/test_notes.py`.  
**API:** identify references/definitions, classify simple/complex, and return deterministic labels/relationships; do not emit final Markdown.  
**Must not write:** `render/markdown.py`, `writer.py`, or target-map ownership.  
**Verification:** standard EPUB metadata, publisher fallback, same-section conversion eligibility, cross-document preservation, ambiguity, nested/rich definitions.

### P4-4 — MathML/ruby/bidi preservation helper

**Writes:** `src/leafmd/transform/rich.py`, `tests/unit/test_rich.py`.  
**Work:** safe-preservation predicates and focused tree tests; extend no renderer code initially.  
**Must not add:** html5lib, LaTeX, network fetching, or a public HTML sanitizer.  
**Verification:** markup/attributes/directional text survive; scripts, event handlers, and unsafe URLs do not.

### P4-5 — Renderer integration (after P4-2/P4-3/P4-4 review)

**Writes:** `src/leafmd/render/markdown.py`, `tests/unit/test_markdown_rich.py`.  
**Work:** invoke the decisions, emit GFM tables/footnotes, retain raw HTML, preserve captions and rich markup, and keep existing text normalization outside protected nodes.  
**Must not redesign:** manifests, planner, TargetMap, or security policy.  
**Verification:** deterministic rendered snippets plus all existing tests.

### P4-6 — Pipeline/report/validation integration

**Writes:** `src/leafmd/render/writer.py` only for orchestration, `src/leafmd/model/report.py` only for approved additive counters if needed, `src/leafmd/validate/output.py`, and focused integration tests.  
**Work:** place transforms at the documented pipeline point; ensure rewritten links/anchors/assets remain valid; optionally record additive rich-content counts without changing schema version.  
**Verification:** current synthetic suite, repeated conversion byte stability, `validate`, and no unresolved links.

### P4-7 — Parent acceptance and integration

**Writes:** parent-owned version/changelog/scoreboard only.  
**Work:** integrate commits in dependency order, run quality gates, reconvert all three probes under `/tmp`, compare structural metrics, and decide whether any remaining defects are Phase 5 or later. Do not commit probe EPUBs or generated trees.

## 7. Delegation and dependency graph

```text
P4-0 (parent contract)
       │
       ├── P4-1 fixtures ───────────────┐
       ├── P4-2 table classifier ───────┤
       ├── P4-3 note classifier ────────┼──→ P4-5 renderer integration
       └── P4-4 rich preservation ──────┘             │
                                                      ↓
                                           P4-6 pipeline/validation
                                                      │
                                                      ↓
                                           P4-7 parent acceptance
```

The initial audit agents characterized the three books and the architecture. Implementation agents are limited to the tickets above; no agent is authorized to broaden Phase 4 or push remotely.

## 8. Acceptance gates

Before integration:

- all ticket-local tests pass;
- `ruff check src tests`, `ruff format --check src tests`, and `mypy` are clean;
- no production dependency on html5lib or a LaTeX converter appears;
- no fixture contains copyrighted prose or uploaded EPUB bytes.

After integration:

- full pytest passes with the existing expected skip(s);
- two consecutive conversions of every synthetic fixture are byte-identical;
- all three probe EPUBs convert and validate successfully;
- simple rectangular probe tables become GFM where the contract permits; spanning/ambiguous tables remain raw without cell loss;
- local simple notes become valid GFM footnotes; Economics-style cross-document notes retain rewritten forward/return links;
- MathML/ruby/bidi synthetic markup survives; dangerous active content and unsafe schemes are removed;
- `book.json`, `toc.json`, and `schema_version` remain compatible;
- no unresolved links or missing generated anchors are introduced.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| markdownify silently loses cell/caption content | classify before rendering; raw-HTML fallback is the default |
| publisher note conventions are mistaken for footnotes | require proven one-to-one local relationships; preserve ambiguous/cross-document links |
| raw MathML/ruby/bidi interacts badly with text normalization | protect rich nodes and test before/after serialization |
| a helper invents anchors or breaks cross-file links | TargetMap is built first and remains the only link/anchor authority |
| report/schema churn blocks consumers | keep schema v1; make counters additive and optional |
| probe outputs become accidental fixtures | keep all EPUBs and generated directories outside git; synthetic fixtures only |
