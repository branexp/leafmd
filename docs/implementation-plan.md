# leafmd — Final Implementation Plan

**Status:** Phase 3 merged on `main` (`a6dee61`, 0.2.0). Phase 4 is planned and delegated on `feat/phase4-rich-content`; no Phase 4 production code has landed yet.
**Date:** 2026-08-16  
**Repo:** `/home/clawdbot/clawd/projects/leafmd` → private `https://github.com/branexp/leafmd`  
**This file is the working build plan.** Use it instead of the original chat plan. GitHub/PR workflow: [github-workflow.md](github-workflow.md).

**Core idea:** parsing EPUB is mostly solved. The product is reconstructing a useful, human-readable semantic book from messy packages.

---

## 0. How to use this document

- Parent agent owns architecture, format contract, security, and reviews.
- Subagents implement isolated tickets listed in §8. Do not reopen §2.
- GitHub remote is `branexp/leafmd` (private). Push remaining tickets as PRs per [github-workflow.md](github-workflow.md). Still do not touch SWAG/DNS/firewall or start a site unless Brandon asks.
- Do not vendor copyrighted EPUBs. Synthetic fixtures only in git.
- Quality gate before calling any ticket done: `python -m pytest`, `ruff check src tests`, `ruff format --check src tests`, `mypy`.

---

## 1. Honest current state (2026-08-16)

This is **not greenfield**. The original 2026-08-16 planning session produced the architecture; a later pass scaffolded the private repo and a Phase 1 vertical slice.

### What exists

| Area | State |
|---|---|
| Identity | `leafmd` 0.2.0, AGPL-3.0-or-later, setuptools `src/` layout |
| CLI | `convert`, `inspect`, `validate`, `report`, `version` (Typer + Rich) |
| Ingest | zip-slip, bomb limits, DRM/`encryption.xml` reject |
| Parse | Direct container/OPF/nav/NCX; EbookLib is a **cross-check only** |
| Plan | Case A default; B merge consecutive un-navved spine files; C split fragment-targeted headings; virtual parts TOC-only |
| Classify | Evidence-ranked (`epub:type` > landmark > nav > guide > NCX > headings > filename/id); types include cover/preface/about-author/other |
| Render | markdownify ATX + drop-cap/hyphen cleanup + simple tables + raw MathML/complex tables |
| Links | Target map + namespaced `src-…` anchors; same-file / `../` / nav fragments; scheme filter; duplicate-id first-wins |
| Assets | Referenced raster/SVG + cover; filename collisions; hostile SVG strip; no remote fetch |
| Output | `book.json`, `toc.json`, `conversion-report.json`, `index.md`, `toc.md`, `content/`, `assets/images/` |
| Docs | architecture, canonical-format, development, security, Copilot review instructions |
| CI | uv venv + ruff + mypy + pytest on 3.11/3.12 |
| Tests | EPUB 2/3, XXE, zip-slip, DRM, fragments, schemes, assets, validator schema, planner B/C, cover, classify, textnorm |

### What is still open

1. No approved goldens (P1-2 / P1-3 still owed before MVP acceptance).
2. Remaining contract docs (P1-4): section-planning, links-and-anchors, validation, fixtures.
3. Optional `--epubcheck` (P1-5). Not an MVP blocker.
4. html5lib is characterization-only (`@pytest.mark.differential`); not a runtime dep.
5. Phase 3 (P3-1…P3-4) is implemented. Goldens/P1-4 remain open and are still owed before MVP.
6. Phase 4 corpus findings and tickets are recorded in [phase4-rich-content.md](phase4-rich-content.md). The three local probe EPUBs are characterization inputs only and must not enter git.

Phase 4 is intentionally conservative: preserve content when a lossless Markdown representation is not proven, keep the existing schema/anchor contract, and do not add html5lib or MathML-to-LaTeX.

### Phase scoreboard

| Phase | Status |
|---|---|
| 0 Planning | Done. Locked decisions in §2 supersede the old five questions. |
| 1 Vertical slice | Closeout coded. Goldens + remaining docs still open. |
| 2 Link/asset correctness | Coded this pass (P2-1…P2-5). |
| 3 Semantic reconstruction | Coded this pass (P3-1…P3-4). Hall reconvert is the acceptance check, not a golden. |
| 4 Rich content | Planned; corpus audit complete; implementation tickets delegated. |
| 5 Robustness | html5lib spike only. No runtime fallback. |
| 6 Library integration | Not started. Remote exists; no library convert yet. |

---

## 2. Frozen decisions

Do not reopen these during implementation.

1. **Name:** repo / package / CLI / import are all `leafmd`.
2. **Visibility:** private until v0.1. Remote is `branexp/leafmd`. Still no public release / PyPI unless asked.
3. **Distribution:** personal library only. Not a public upload service.
4. **Source of truth:** EPUB. Output is regenerate-only. No edit overlay in v1.
5. **Future site host:** `book.pettee.org` later. Converter stays SSG-agnostic.
6. **License:** AGPL-3.0-or-later because v1 links EbookLib. Not legal advice.
7. **Runtime:** Python 3.11+, CLI-only, flags only, no config file, no daemon.
8. **Output shape:** flat `content/` + `assets/images/` + the five index files. Hierarchy lives in `toc.json`.
9. **Parser truth:** our OPF/nav/NCX parse is authoritative. EbookLib never supplies `book.toc`. Nothing above `leafmd.parse.ebooklib_adapter` imports `ebooklib`.
10. **Phase 1 planner:** case A only (one spine document → one file). Cases B/C wait for Phase 3.
11. **`linear="no"`:** include as its own file and emit `PLAN_NONLINEAR` info. Do not delete. Reading order stays spine order.
12. **Anchors:** namespaced explicit HTML `<a id="src-<stem>-<id>"></a>` is the compatibility contract. Astro/github-slugger heading ids are not.
13. **TOC fragments:** rewrite through the **same** global target map as content links. Never emit original EPUB ids in `toc.json` / `toc.md`.
14. **Links:** keep `http` / `https` / `mailto`. Drop `javascript:`, `data:`, `file:`, `vbscript:`, and unknown schemes. No network I/O.
15. **Assets:** copy referenced JPEG/PNG/GIF/WebP/SVG and the cover. Skip fonts/CSS/JS/audio/video/SMIL with `MEDIA_SKIPPED`.
16. **Math:** preserve MathML as raw HTML. No MathML→LaTeX in v1.
17. **Notes / rich tables / ruby / bidi:** Phase 4. Do not pretend they exist in Phase 1 docs.
18. **EPUBCheck:** optional `--epubcheck` only. Store under `source_validation`. Never mix into converter issues.
19. **Trust:** `untrusted EPUB → leafmd → library-trusted book dir → site sanitizer → public HTML`. Converter output is not a public-HTML trust boundary.
20. **Toolchain:** uv, setuptools, ruff, pytest, mypy. No Pandoc, no Pydantic-everywhere, no tox/nox, no PyPI until asked.

---

## 3. Architecture (as built + target)

```text
EPUB ZIP
  → ingest guards (paths, bombs, DRM)
  → direct ZIP/OPF/nav/NCX parse
  → optional EbookLib cross-check (spine nonempty)
  → NormalizedPublication
  → SectionPlanner (Phase 1: spine item → file)
  → TargetMap + asset copy
  → rewrite tree
  → rich-content classify/normalize (Phase 4)
  → LeafmdConverter (markdownify)
  → BookDirectory writer
  → OutputValidator → conversion-report.json
```

### Module map

```text
src/leafmd/
  cli.py
  convert.py                 # thin orchestration
  inspect_cmd.py
  errors.py
  report.py
  model/                     # public IR; no ebooklib
  ingest/archive.py          # hostile ZIP
  parse/
    ebooklib_adapter.py      # import ebooklib here only
    package.py               # container.xml + OPF
    navigation.py            # nav + NCX + guide
    html.py                  # lxml XML, lxml HTML recover
    hrefs.py
    xmlutil.py               # resolve_entities=False, no_network
  semantics/
    classify.py              # title/filename rules (Phase 1)
    plan.py                  # case A
    evidence.py              # Phase 3
  transform/
    links.py                 # TargetMap + rewrite
    assets.py
    slug.py
    slice.py / merge.py      # Phase 3
    notes.py / tables.py     # Phase 4
  render/
    markdown.py
    writer.py
  validate/
    output.py
    epubcheck.py             # Phase 5 / optional P1-5
```

### Invariants

- Semantic/render code sees only `leafmd.model` types.
- Target map is built **before** render. It is the single anchor contract.
- Writer emits filesystem + manifests. Validator re-reads the directory and does not trust in-memory plans blindly.
- Determinism: `sec-001`, `{order:03d}-{type}-{slug}.md`, sorted JSON keys, no wall-clock timestamps in Markdown.

---

## 4. Canonical output (contract)

```text
<book-slug>/
  index.md
  toc.md
  book.json
  toc.json
  conversion-report.json
  content/
    001-chapter-welcome.md
  assets/
    images/
```

- `book.json` is the bibliographic + section manifest.
- `toc.json` is the navigation tree (`nav` > `ncx` > inferred from spine).
- Frontmatter is non-redundant: `id`, `title`, `type`, `order`, `source[]`. No prev/next/total.
- Relative asset paths from `content/*.md` are `../assets/images/…`.
- Leafmd Markdown: UTF-8, YAML frontmatter, CommonMark, GFM tables, ATX headings, fenced code, raw HTML for explicit anchors / MathML / complex tables.

Full field notes live in `docs/canonical-format.md`. Expand that doc during P1-4; do not invent Astro/MDX fields.

---

## 5. Known defects to fix before MVP

These are real bugs in current code, not future features.

| ID | Defect | Where | Fix |
|---|---|---|---|
| D1 | `posix_join()` drops fragments | `parse/hrefs.py`, `transform/links.py` | **Fixed** in P1-1 / P2-1. |
| D2 | TOC emits original EPUB fragment ids | `render/writer.py` | **Fixed** in P1-1. TOC uses TargetMap. |
| D3 | `validate` skips `#…` hrefs | `validate/output.py` | **Fixed** in P2-3. Same-file, cross-file, and TOC fragments checked. |
| D4 | Explicit anchors may not survive markdownify | `render/markdown.py` | **Fixed** in P1-1 / P2-1. Duplicate source ids inject once. |
| D5 | XXE fixture can crash on non-string lxml tags | `parse/xmlutil.py` | **Fixed** in P1-1. |
| D6 | Scheme filter requires `://` | `transform/links.py` | **Fixed** in P2-1. `javascript:` / `data:` / `file:` dropped. |
| D7 | pytest collection path | `pyproject.toml` | **Fixed** in P1-0. |
| D8 | mypy 15 errors | package/navigation/markdown/validate | **Fixed** in P1-1. |
| D9 | SVG sanitize is regex-only | `transform/assets.py` | **Hardened** in P2-2 (script/event/handler/foreignObject/external href). Parse-based sanitize still Phase 5. |
| D10 | Classifier ignores `epub:type` / landmarks | `semantics/classify.py` | Leave for Phase 3; document as title-rule only. |

---

## 6. CLI contract

```text
leafmd convert BOOK.epub [--output DIR] [--strict] [--epubcheck] [--verbose] [--debug]
leafmd inspect BOOK.epub [--json]
leafmd validate BOOKDIR [--json]
leafmd report BOOKDIR
leafmd version
```

| Exit | Meaning |
|---|---|
| 0 | ok / warnings only |
| 1 | completed with errors |
| 2 | fatal |
| 3 | usage |

- v1 is single-book. Recursive batch is Phase 6.
- `--strict` promotes `LINK_UNRESOLVED`, `ASSET_MISSING`, `RENDER_MISSING_SOURCE` to errors (already sketched in `convert.py`).
- `--epubcheck` is optional and not a Phase 1 acceptance blocker.

---

## 7. Phases

### Phase 1 — vertical slice (closeout now)

Well-formed EPUB 2/3, one XHTML ≈ one file:

- ingest guards + direct OPF/nav/NCX + EbookLib cross-check
- spine-ordered files, nav titles when they map 1:1
- markdownify ATX
- referenced images + SVG + cover
- global link rewrite + explicit anchors + TOC rewrite
- writer + report + `inspect` / `validate`
- goldens for the two committed fixtures
- remaining contract docs
- green `pytest` / `ruff` / `mypy`

**Acceptance (committed EPUB 2 + EPUB 3 fixtures):**

1. Metadata, spine, and nav are read.
2. Each content document in spine order becomes a Markdown file (`linear="no"` included and reported).
3. Internal links and TOC targets resolve through namespaced anchors. No duplicate output anchors.
4. Referenced JPEG/PNG/SVG and cover are copied; SVG stays SVG.
5. Every file has provenance.
6. Recoverable problems warn; fatals are clear.
7. The five index files exist.
8. Unit + golden tests pass via `python -m pytest`. mypy and ruff are clean.

### Phase 2 — link/asset correctness

Duplicate ids, cross-file `../` fragments, cover provenance, missing resources, stronger SVG sanitize, report completeness, scheme filtering, validator schema checks.

### Phase 3 — semantic reconstruction

Evidence table (`epub:type` > landmark > nav > guide > NCX > headings > filename).  
Case B merge, case C in-file split, virtual parts, conflict reports.

### Phase 4 — rich content

GFM footnotes for simple notes; complex notes preserved; rectangle+header GFM tables; caption policy; MathML fixtures; ruby/bidi.

### Phase 5 — robustness

html5lib fallback, malformed suite, optional Docker EPUBCheck, `LEAFMD_CORPUS` private corpus.

### Phase 6 — library integration

`leafmd convert DIR --recursive`, `library/books/<slug>/` convention. Still no daemon. Private GitHub repo is `branexp/leafmd`.

### Explicitly deferred

MOBI/AZW3/PDF; DRM bypass; cache/incremental; DB; multiprocessing; media overlays; fonts/CSS; MathML→LaTeX; annotation overlay; website; SWAG/DNS; public convert API; PyPI automation.

---

## 8. Next coding pass — tickets and subagent cut-points

Parent reviews every ticket. One write-scope per agent. No overlapping files.

### Must stay with the parent

- Architecture and module boundaries
- Canonical JSON / frontmatter / anchor contract
- `linear="no"` and TOC-fragment policy (already frozen in §2)
- Security policy (ZIP limits, XML entities, URL schemes, SVG, EPUBCheck execution)
- CLI names, exit codes, `--strict` promotion set
- Approving goldens
- Planner B/C algorithm (Phase 3)

### Excellent for subagents

- Fixture families
- Golden harness mechanics
- Isolated parser/renderer spikes
- Validator unit tests after the contract is written
- Docs that describe already-frozen behavior
- Characterization tests that fail against current case-A planner

### Sequence

```text
P1-0 quality gate          parent or one closeout agent
P1-1 anchors + XXE         parent-owned implementation
        ↓
   ┌────┼──────────────┬──────────────┬──────────────┐
P1-2   P1-3           P1-4           P2-4           P2-5
goldens fixtures      docs           html5lib spike B/C fixtures
   └────┼──────────────┴──────────────┴──────────────┘
        ↓
P2-1 fragment/TOC map      after P1-1, parent reviews invariant
P2-2 assets                parallel with P2-1 if files don’t overlap
P2-3 validate/report       after P2-1 contract
P1-5 --epubcheck           optional; after parent writes the contract
        ↓
approve goldens, then stop. Do not start Phase 3 implementation.
```

### Tickets

#### P1-0 — Make the quality gate runnable

- **Owner:** parent or one subagent
- **Write:** `pyproject.toml` pytest `pythonpath`, maybe `tests/conftest.py`
- **Work:** `python -m pytest` and `.venv/bin/pytest` both collect; document the invocation in `docs/development.md`
- **Verify:** `pytest --collect-only` lists integration + unit tests
- **Avoid:** production behavior changes

#### P1-1 — Restore Phase 1 acceptance (block all goldens)

- **Owner:** parent-reviewed implementation subagent
- **Write:** `parse/xmlutil.py`, `parse/hrefs.py`, `transform/links.py`, `render/markdown.py`, `render/writer.py` only as needed
- **Work:** D1, D4, D5. Emit explicit `src-…` anchors. Don’t crash on entity/comment nodes. Preserve path+fragment through join/resolve.
- **Verify:** EPUB 3 fixture contains `src-ch01-p1` or `src-ch01-welcome`; XXE does not contain `root:` and does not raise; ruff + mypy on touched files
- **Avoid:** planner, fixtures architecture, JSON schema redesign

#### P1-2 — Golden harness

- **Owner:** subagent
- **Write:** `tests/golden/`, one test module, opt-in update flag (`--update-goldens` or env)
- **Work:** compare approved trees for current EPUB 2 and EPUB 3 builders. Normalize only `tool_version` if needed.
- **Verify:** two consecutive converts match; CI never auto-updates
- **Avoid:** production code. Wait to *approve* goldens until after P1-1 / P1-3 settle.

#### P1-3 — Phase 1 acceptance fixtures

- **Owner:** subagent
- **Write:** `tests/fixtures/epub_builder.py` + new tests only
- **Add builders:** JPEG; cross-file fragment; same-file fragment; TOC fragment; nav vs spine order; missing image; `linear="no"`; no nav / empty NCX; metadata edge; no-image book
- **Verify:** each fixture asserts one report code or one output invariant; then `validate_book_directory`
- **Avoid:** inventing Phase 3 split/merge behavior

#### P1-4 — Contract docs

- **Owner:** docs subagent; parent reviews wording
- **Write:**  
  `docs/section-planning.md`  
  `docs/semantic-classification.md`  
  `docs/links-and-anchors.md`  
  `docs/validation.md`  
  `docs/fixtures.md`  
  plus light edits to README / architecture / canonical-format / development
- **Work:** document **current** Phase 1 behavior. Label B/C, footnotes, html5lib, EPUBCheck as later.
- **Avoid:** production code; site/API promises

#### P1-5 — Optional `--epubcheck` (not an MVP blocker)

- **Owner:** parent writes contract; subagent implements runner
- **Write:** `validate/epubcheck.py`, CLI flag, mocked tests
- **Work:** Docker `w3c/epubcheck`, no network, timeout, `source_validation.epubcheck` only
- **Avoid:** host Java, daemon, firewall, mixing codes into converter issues

#### P2-1 — Fragment / duplicate-id map

- **Owner:** parent invariant, then implementation subagent
- **Write:** `transform/links.py`, writer TOC helpers, focused tests
- **Work:** same-file, cross-file, `../`, nav fragments, duplicate ids (`-2`), `LINK_UNRESOLVED`
- **Verify:** every generated fragment resolves in `validate`
- **Avoid:** slice/merge

#### P2-2 — Assets

- **Owner:** subagent
- **Write:** `transform/assets.py` + tests
- **Work:** missing bytes, cover EPUB2 meta vs EPUB3 `cover-image`, filename collisions, hostile SVG cases, `ASSET_REMOTE`
- **Avoid:** fonts/CSS/AV

#### P2-3 — Validator / report completeness

- **Owner:** parent contract, then subagent
- **Write:** `validate/output.py`, `model/report.py` tests
- **Work:** required JSON fields, TOC fragment anchors, duplicate output paths, asset existence, `--strict`, conversion-report consistency
- **Avoid:** new canonical fields without parent approval

#### P2-4 — html5lib spike (characterization only)

- **Owner:** subagent
- **Write:** spike notes + tests under `tests/`; no mandatory dependency unless parent accepts
- **Work:** which malformed XHTML lxml recover misses; entity/network still off
- **Avoid:** silently adding html5lib to runtime deps

#### P2-5 — Planner B/C characterization fixtures

- **Owner:** subagent fixtures; parent algorithm later
- **Write:** fixtures + failing tests that document the desired contract
- **Work:** one XHTML / many chapters; many XHTML / one chapter; virtual part
- **Avoid:** implementing heuristics in this pass

### Phase 3 tickets (authorized 2026-08-16)

Brandon asked to implement Phase 3 now. Goldens/P1-4 stay open and are **not** blockers for this pass. Do **not** implement Phase 4 tables/math/notes.

One write-scope per agent. Parent integrates, bumps to **0.2.0**, updates `CHANGELOG.md`, reconverts the Hall EPUB under `/tmp` + gitignored `tmp-convert/`, then opens one PR.

#### P3-1 — Cover discovery

- **Owner:** isolated implementer
- **Write:** `src/leafmd/parse/package.py`, `tests/unit/test_cover.py`, and a new builder in `tests/fixtures/epub_builder.py` only if needed
- **Work:** resolve `cover_id` from EPUB2 `<meta name="cover">`, EPUB3 `properties="cover-image"`, then OPF guide (`cover` / `other.ms-coverimage-standard`), then manifest item id `cover` / `coverimagestandard` when that item is an image. If the cover item is an XHTML document, follow its first local image. If still missing after a referenced cover image exists, emit `COVER_MISSING`.
- **Verify:** synthetic guide-only cover lands in `book.json.cover` and `assets/images/`; existing EPUB2/3 cover tests still pass
- **Avoid:** `writer.py`, planner, classifier, Hall EPUB, version bump

#### P3-2 — Evidence-ranked classification

- **Owner:** isolated implementer
- **Write:** `src/leafmd/semantics/classify.py`, optional new `src/leafmd/semantics/evidence.py`, `tests/unit/test_classify.py`
- **Work:** rank evidence `epub:type` > landmark > nav label > guide > NCX > in-document headings > filename/id. Add types: `cover`, `preface`, `about-author`, `other` (back-matter ads). Do not classify a document as `chapter` when the only title is the book title or `.`. Keep rules explainable (no ML).
- **Verify:** preface/cover/about-author unit tests; existing preface/default tests updated to the new API if needed
- **Avoid:** `plan.py`, `package.py`, renderer, version bump

#### P3-3 — Planner B/C + virtual parts + TOC union

- **Owner:** isolated implementer; start **after** P3-2 lands or rebase onto it
- **Write:** `src/leafmd/semantics/plan.py`, `src/leafmd/semantics/__init__.py`, `src/leafmd/transform/slice.py`, `src/leafmd/transform/merge.py`, `src/leafmd/render/writer.py` TOC helpers only, `tests/unit/test_planner_bc.py`
- **Work:** keep case A default. Case B: merge consecutive spine XHTML that share one nav/NCX chapter entry (Hall index `in1` + `in1_b`). Case C: split one XHTML with multiple top-level chapter headings / nav fragments into multiple files. Virtual parts: TOC node with children and `section_id: null` (no content file). TOC tree is nav ∪ NCX (nav titles win on the same href; union adds nav-only nodes such as a preface). Un-xfail the P2-5 desired tests and keep a case-A regression.
- **Verify:** `pytest tests/unit/test_planner_bc.py` all pass (no xfail); `linear="no"` still emits `PLAN_NONLINEAR` as its own file
- **Avoid:** `package.py`, `classify.py` internals, `markdown.py`, goldens, Hall EPUB, version bump

#### P3-4 — Text cleanup (not Phase 4 tables)

- **Owner:** isolated implementer
- **Write:** `src/leafmd/transform/textnorm.py`, `src/leafmd/render/markdown.py`, `src/leafmd/render/writer.py` `_index_markdown` only, `tests/unit/test_textnorm.py`
- **Work:** (1) drop-cap / first-letter: `**T**hen` → `Then` when a single bold/styled first letter is followed by the rest of the word. (2) end-of-line hyphenation: `seclu- sive` → `seclusive` only for `[A-Za-z]{2,}-\s+[a-z]`. (3) promote a leading bold title block to an ATX heading when the section has no `h1`–`h3`. (4) convert OPF description HTML in `index.md` (`<p>`, `<BR>`, `<i>`) to Markdown; do not emit a literal truncated `...` unless the source itself ends that way. Do **not** “fix” OCR (`tluee`, `modem`).
- **Verify:** unit tests for each transform; existing convert tests still pass
- **Avoid:** planner, classifier, `package.py`, tables/MathML, version bump

#### P3-5 — Parent integration (not a subagent)

- **Owner:** parent
- **Write:** `pyproject.toml` version, `src/leafmd/__init__.py` `__version__`, `CHANGELOG.md`, plan/docs scoreboard
- **Work:** merge P3-1…P3-4, run full quality gate, reconvert the Hall EPUB to `/tmp/leafmd-secret-teachings` and gitignored `tmp-convert/secret-teachings`, confirm cover + titles + preface + drop-cap + `index.md` description, then open one PR
- **Avoid:** committing the EPUB or converted tree

---

## 9. Test strategy

### Layers

| Layer | Now | Next |
|---|---|---|
| Unit | slug, href, classify | anchors, schemes, nav/OPF, assets, report codes, planner A edges |
| Synthetic | EPUB2/3, XXE, zip-slip, DRM, broken link | §8 P1-3 list |
| Golden | none | EPUB2 + EPUB3 first; more in later phases |
| Public | none | optional `@pytest.mark.online`, pinned SHA, license check |
| Private | none | `LEAFMD_CORPUS`, skip if unset |
| Differential | none | dev-only; EbookLib vs our OPF; not CI |

### Markers to register

`unit`, `synthetic`, `integration`, `golden`, `security`, `slow`, `online`, `private`, `differential`, `epubcheck`

CI default:

```text
pytest -m "not online and not private and not differential and not epubcheck"
```

### Golden vs assertion

- **Golden:** tiny representative trees (shape, Markdown, anchors, assets).
- **Assert:** report codes, fatals, path containment, schemes, provenance, determinism.
- Do not golden every fixture.

### Security tests still owed

ZIP slip (`../`, absolute, backslash, drive letter), bombs (count / size / ratio), bad zip, empty spine, XXE/DTD/billion-laughs, no network, drop `script`/`iframe`/`object`/`embed`/`form`/`on*`, drop unsafe schemes, SVG script/event/external href, output path escape, no symlink follow.

### Later fixture batches (non-overlapping)

| Agent | Family |
|---|---|
| A | package / nav / NCX / metadata |
| B | links, fragments, duplicate ids, covers, missing assets |
| C | split / merge / front-back matter (Phase 3) |
| D | tables, notes, MathML, ruby, bidi (Phase 4) |
| E | hostile ZIP/XML/SVG |
| F | public-sample license harness + `LEAFMD_CORPUS` |
| Reviewer | approve goldens; never generate and approve the same tree |

---

## 10. NFRs

| NFR | Target |
|---|---|
| Correctness | Preferred over speed |
| Scale | 1–300 books, offline |
| Perf | Typical 300-page book in a few seconds |
| Memory | Refuse above ingest caps (200 MB uncompressed / 20 MB member / 20k entries / ratio 100) |
| Availability | CLI, not a service |
| Security | Hostile input; no network |
| Maintainability | Typed models, goldens, small pipeline surface |

---

## 11. Risks

1. Semantic planning unbounded → ship A now; B/C behind fixtures.
2. EbookLib TOC lies on EPUB 3 → already mitigated; keep ignoring `book.toc`.
3. Malformed XHTML → recover + report; html5lib is Phase 5.
4. Astro sanitizer vs raw HTML/MathML/SVG → site problem later; converter still emits explicit anchors.
5. AGPL if this becomes a hosted converter → keep it a local CLI.
6. Copyrighted fixtures in git → synthetics only.
7. Scope creep into the reading site → format freeze; site is a later repo.

---

## 12. OpenClaw operating rules for the build

- Parent keeps this file current when a ticket lands or a decision changes.
- Spawn **isolated** subagents with a single ticket id, write-scope, and verification command.
- Do not spawn research swarms unless a dependency changes.
- Coding-agent skill is fine for a large isolated ticket; not for one-file edits.
- Durable product facts can be folded into `MEMORY.md` after Brandon is using the tool. Until then, this file is enough.
- Remote exists. Ask before force-push, history rewrite, making the repo public, or PyPI publish.

---

## 13. Need from Brandon (nothing blocking closeout)

Already answered and locked:

1. private  
2. `leafmd`  
3. personal library only  
4. regenerate-only  
5. `book.pettee.org`

Still optional, not blocking Phase 1:

- Include `--epubcheck` in this closeout, or wait for Phase 5?

Default if unasked: skip EPUBCheck for MVP. GitHub remote is created.
