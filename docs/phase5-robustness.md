# Phase 5 — Robustness and source validation

**Status:** Planned; no Phase 5 production implementation has started.

**Depends on:** Phase 4 rich-content reconstruction, merged in `main` as `0.3.0`.

**Related plan:** [implementation-plan.md](implementation-plan.md) §7 and §8.

Phase 5 hardens the converter against malformed-but-common EPUB inputs and hostile package structures without changing the canonical book-directory contract. It is a reliability phase, not a new output-format phase.

## 1. User value

A personal library contains books from different publishers and production pipelines. Some are valid EPUB 2/3 packages; others contain recoverable XHTML damage, inconsistent encodings, broken ZIP metadata, malformed SVG, or source-validation errors. Phase 5 should make those cases:

- recoverable when a safe, deterministic tree can be produced;
- diagnosable when recovery is lossy or impossible;
- bounded against resource-exhaustion and path-escape attacks; and
- reproducible in synthetic tests and private manual characterization.

The default conversion path must remain lightweight and offline. A normal conversion must not require html5lib, Docker, Java, or network access.

## 2. Frozen boundaries

Phase 5 preserves all existing contracts:

- `schema_version: 1`, the five index files, flat `content/`, and `assets/images/` remain unchanged;
- explicit `src-<stem>-<id>` anchors and the global target-map rules remain authoritative;
- OPF, nav, and NCX continue to be parsed as XML by the existing safe lxml path;
- EbookLib remains a cross-check only;
- output remains regenerate-only and intended for a private personal library;
- converter output is not declared safe public HTML;
- no DRM bypass, network fetching, remote asset retrieval, or automatic Docker image pull;
- no MathML-to-LaTeX, site integration, recursive library conversion, database, daemon, PyPI release, or public API.

Phase 5 may add an optional recovery dependency and an explicit `--epubcheck` flag, but neither changes the default behavior when unused.

## 3. Workstreams

### P5-0 — Baseline, contracts, and approved goldens

Before changing recovery behavior:

1. Approve the committed EPUB 2 and EPUB 3 golden trees required by the Phase 1 MVP gate.
2. Record which fields are normalized as volatile (`tool_version`, timestamps if ever introduced) and which are exact contracts.
3. Freeze parser-recovery issue codes and the `source_validation.epubcheck` result shape before implementation tickets begin.
4. Add a deterministic conversion comparison helper that compares structure, links, anchors, assets, and report codes without comparing unstable prose.

Goldens are approval artifacts, not a reason to make malformed input look correct. A recovery change must update a golden only when the expected canonical output has been reviewed explicitly.

### P5-1 — Bounded malformed-XHTML recovery

The current parser tries safe lxml XML parsing and lxml HTML recovery. Phase 5 will make the recovery boundary explicit and measurable.

**Required behavior:**

- Valid XHTML continues through the existing XML path with entity resolution, DTD loading, and network access disabled.
- The package document, container, nav, NCX, and other metadata XML never use an HTML recovery parser; metadata semantics must not be guessed from broken HTML.
- Spine XHTML/HTML resources may use an optional html5lib-backed recovery candidate only after the lxml result is unusable or fails a defined structural-recovery predicate.
- lxml remains the first choice whenever it produces a usable tree. html5lib is not a wholesale renderer replacement.
- The html5lib candidate is converted to the same lxml-based internal tree boundary before slicing, link rewriting, rich transforms, and rendering.
- The fallback is attempted at most once per source document and is bounded by the existing archive/member limits.
- A recovery decision records the parser used and whether recovery occurred. It must not silently hide a malformed source.
- If html5lib is not installed, normal lxml recovery remains available. If neither parser produces a usable content tree, conversion fails with a stable fatal parse code rather than writing a partial book.

**Optional dependency shape:** keep html5lib out of the default install. A dedicated optional extra or development environment may install it for Phase 5 recovery. The exact supported version is frozen in the P5-0 contract and tested on Python 3.11 and 3.12.

**Candidate recovery cases:**

- unclosed, misnested, or implicitly closed paragraphs and sections;
- missing `html`, `head`, or `body` wrappers;
- inconsistent HTML/XHTML casing and namespace presentation;
- truncated tags and incomplete end tags;
- recoverable character-encoding declarations and replacement characters;
- comments and processing instructions adjacent to content;
- malformed table/list nesting where a safe tree can still be identified.

The fallback must not invent chapter boundaries, repair links by guessing, or turn an unusable document into a successful empty section. Existing planner, target-map, and anchor contracts remain in force after recovery.

### P5-2 — Malformed and hostile package fixture suite

Expand synthetic in-memory fixtures; do not commit real books or EPUB binaries.

**Archive cases:**

- truncated ZIP and invalid central-directory records;
- duplicate member names and conflicting file metadata;
- absolute paths, `../`, backslashes, drive-letter paths, and mixed-separator traversal;
- symlink-like entries and entries whose normalized output path escapes the book directory;
- compression-ratio, member-size, total-size, and entry-count boundary conditions;
- missing or malformed `mimetype`, container, OPF, manifest, spine, nav, or NCX records.

**XML and content cases:**

- internal and external entities, parameter entities, DTDs, and billion-laughs-shaped payloads;
- malformed XML declarations, invalid bytes, NUL bytes, and truncated resources;
- duplicate ids, broken fragments, missing resources, unsafe schemes, and active HTML elements;
- output links and anchors that attempt to escape `content/` or the book root.

Tests must assert stable report codes and security outcomes, not only message substrings. No fixture may perform network I/O; tests should fail if a parser or subprocess attempts it.

### P5-3 — Parse-based SVG sanitization

Phase 2 added regex-based SVG hardening. Phase 5 will add a safe XML-tree sanitizer for SVG while retaining a conservative fallback for inputs that cannot be parsed safely.

The sanitizer will:

- parse with entity expansion, DTD loading, and network access disabled;
- remove scripts, event-handler attributes, `foreignObject`, active animation or HTML payloads, and external references;
- reject or remove unsafe `href` / `xlink:href` values and non-local resource references;
- preserve safe drawing elements and useful presentation attributes where parsing is unambiguous;
- keep copied assets inside the generated `assets/images/` directory; and
- report sanitization or rejection without turning a safe book conversion into a silent success with dangerous content.

Fixtures must cover valid SVG, malformed SVG, external entity attempts, external URLs, nested active elements, namespace variants, and safe viewBox/presentation attributes.

### P5-4 — Optional Docker EPUBCheck runner

Add the currently deferred `--epubcheck` option as an explicit, non-default source-validation path:

```text
leafmd convert BOOK.epub --output out/the-book --epubcheck
```

The runner will:

- use a pinned, documented EPUBCheck image/version;
- never pull an image automatically;
- run with a read-only source mount, an isolated temporary workspace, no network, a timeout, and bounded stdout/stderr;
- treat the EPUBCheck process as untrusted input and parse only the supported diagnostic output;
- preserve conversion output even when EPUBCheck reports source errors; and
- clean temporary files on success, failure, timeout, and interruption.

Results belong under the existing `conversion-report.json` `source_validation.epubcheck` namespace, for example:

```json
{
  "requested": true,
  "status": "passed|failed|unavailable|timed_out|error",
  "tool": "EPUBCheck",
  "version": "...",
  "exit_code": 0,
  "messages": []
}
```

The exact additive fields and status vocabulary are frozen in P5-0. EPUBCheck findings are not copied into converter `issues`, do not become link/asset/parser issue codes, and do not change the canonical schema. Missing Docker/image availability is a visible `unavailable` result, not an implicit network pull. Tests mock the subprocess by default; a real-image test is optional and marked `epubcheck`.

### P5-5 — Private corpus characterization and reproducibility

Use `LEAFMD_CORPUS` only as a local, manual characterization input. It is not committed and is not part of default CI.

The corpus runner will record only safe summaries such as:

- source identifier supplied by the operator;
- parser/recovery path used;
- output file and asset counts;
- issue-code counts and unresolved-link counts;
- duplicate-anchor and output-path violations;
- elapsed time and peak-size counters where available; and
- deterministic comparison results for repeated conversion of the same input.

It must not copy EPUB content into logs, commit generated trees, or require a website. Every corpus-discovered bug that is fixed becomes a small synthetic regression fixture before the corpus case is considered resolved.

## 4. Functional requirements

These are the Phase 5 contracts to freeze before implementation:

- **FR-1 — Default parser stability:** When a source document is valid or safely recoverable by lxml, the converter shall use the existing lxml path and preserve the Phase 4 output contracts.
- **FR-2 — Optional recovery:** When a spine content document is structurally unusable after lxml recovery and html5lib is installed, the converter shall try exactly one bounded html5lib candidate and record the recovery path.
- **FR-3 — Missing recovery dependency:** When html5lib is unavailable, the converter shall not fail installation or normal conversion solely because it is absent; it shall use usable lxml output or emit a stable fatal parse result when no usable tree exists.
- **FR-4 — Security invariants:** Regardless of parser path, entity expansion, DTD/network access, active HTML, unsafe schemes, output traversal, and unsafe SVG references shall remain blocked.
- **FR-5 — Archive bounds:** When an archive crosses a configured path, count, size, or compression-ratio limit, the converter shall reject it before writing a book directory.
- **FR-6 — EPUBCheck opt-in:** When `--epubcheck` is absent, the converter shall not invoke Docker, Java, EPUBCheck, or network access. When it is present, the converter shall record a bounded source-validation result without changing the canonical output schema.
- **FR-7 — Determinism:** Given identical input bytes, dependency versions, and options, repeated conversion shall produce equivalent canonical files, anchors, links, assets, and issue codes.
- **FR-8 — Corpus isolation:** Corpus characterization shall remain opt-in, local, and excluded from git and CI.

## 5. Acceptance criteria

Phase 5 is complete only when all of the following are true:

1. Approved EPUB 2/3 goldens pass without an unreviewed drift.
2. Synthetic malformed-XHTML fixtures prove deterministic lxml-first recovery and the optional html5lib path.
3. The default environment passes with no html5lib, Docker, Java, or network dependency.
4. Security fixtures cover the broader ZIP, XML/DTD, SVG, no-network, symlink, and output-path cases listed above.
5. A malformed source either yields a validated book with an explicit recovery report or a clear fatal code; no silent empty/partial output is accepted.
6. `leafmd convert --epubcheck` reports `passed`, `failed`, `unavailable`, `timed_out`, or `error` under `source_validation.epubcheck` and never performs an automatic image pull.
7. Repeated conversion of the same synthetic fixtures is deterministic.
8. Private corpus runs remain outside CI and produce no committed source or output data.
9. `ruff check src tests`, `ruff format --check src tests`, `mypy`, and the default pytest suite pass on Python 3.11 and 3.12.
10. The canonical schema, explicit-anchor contract, report top-level keys, and Phase 4 rich-content behavior remain compatible.

## 6. Ticket sequence and write scopes

Tickets should remain isolated and land as separate PRs unless the parent deliberately consolidates them:

| Ticket | Scope | Main write areas | Depends on |
|---|---|---|---|
| P5-0 | recovery/report contract, golden approval, acceptance harness | docs, golden harness, report contract tests | Phase 4 merged |
| P5-1 | lxml-first/html5lib recovery | `parse/html.py`, optional dependency metadata, parser tests | P5-0 |
| P5-2 | malformed archive/XML/security fixtures and boundary fixes | ingest/parse security modules, synthetic fixtures/tests | P5-0 |
| P5-3 | parse-based SVG sanitizer | `transform/assets.py`, SVG fixtures/tests | P5-0 |
| P5-4 | optional Docker EPUBCheck | CLI/convert/report integration and mocked runner tests | P5-0 |
| P5-5 | private corpus runner and characterization notes | local-only tooling/docs; no corpus data | P5-1 through P5-4 |

Parent-owned decisions are parser selection, security boundaries, report vocabulary, canonical output changes, and golden approval. An implementation agent may not add a parser fallback, Docker invocation, or new report code outside its ticket contract.

## 7. Explicit non-goals

Phase 5 does **not**:

- bypass DRM or repair encrypted packages;
- fetch remote images, schemas, Docker images, or validation services during conversion;
- turn converter Markdown/raw HTML into public-safe HTML;
- add recursive directory conversion or the `library/books/<slug>/` convention (Phase 6);
- add a database, daemon, multiprocessing, cache, or incremental editing model;
- convert fonts, CSS, audio/video, SMIL, MathML, or annotations into new output systems; or
- publish the package, repository, corpus, or generated libraries.
