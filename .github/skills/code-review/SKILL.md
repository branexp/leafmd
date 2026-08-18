---
name: code-review
description: "Review leafmd pull requests for hostile-EPUB safety, parser/anchor/image-analysis contracts, scope, and missing tests. Use for Copilot code review and any PR review of this repository."
---

# leafmd code review

Use this skill on leafmd pull requests. Custom instructions hold standing rules; this file is the review procedure.

Read first:

1. PR title/body and stated scope
2. Diff plus only the nearby call sites needed to understand it
3. `.github/copilot-instructions.md`
4. Matching `.github/instructions/*.instructions.md`
5. Current contract docs (`README.md`, architecture, canonical-format, security) when behavior is in dispute

`docs/implementation-plan.md` is historical context, not a frozen specification.

## Severity

- **Blocker:** DRM bypass; XML entity/DTD/network regression; core remote fetch; active-content/scheme escape; output path escape; raw EPUB ids breaking TOC/anchor integrity; EbookLib leaking above its adapter; copyrighted/private data committed
- **Must-fix:** broken shipped contract such as missing `src-*` anchors, fragment loss, dropped `linear="no"`, unsafe image-analyzer replacement, missing fail-open behavior, or CI-breaking typing/runtime errors
- **Should-fix:** missing regression test, unrelated churn, unstable message-only assertion, misleading docs/security claim, behavior/public-CLI change without an `Unreleased` changelog entry, or release version mismatch
- **Nit:** style only when it would fail configured tooling; skip taste nits

If nothing reaches should-fix, keep the review summary short.

## Pass 1 — scope and metadata

- Confirm the PR has one coherent purpose; flag unrelated production/docs/test churn.
- Docs-only PRs should not silently change production behavior.
- Test-only PRs may add explicit characterization coverage but should not normalize intentional default-suite failures.
- Behavior/public-CLI changes should update `CHANGELOG.md` under `Unreleased`. Release PRs must keep `pyproject.toml` and `src/leafmd/__init__.py` versions identical.

## Pass 2 — hostile input and external boundaries

For ingest/parse/transform/render/validate/image changes, check the boundaries actually implemented:

- `META-INF/encryption.xml` / DRM remains rejected
- XML entity resolution, DTD loading/validation, and parser network access remain off
- archive code still reads members in place; do not invent ZIP-bomb/member-path requirements that current policy intentionally omits
- active HTML/event handlers and unsafe URL schemes do not survive
- remote EPUB assets are not fetched
- SVG hardening is not weakened and is not falsely treated as a complete sanitizer
- output/validator paths cannot escape the generated book directory
- optional analyzers remain opt-in and external; leafmd does not silently install/fetch Paddle/models
- analyzer failures/missing/unsupported results preserve original images and do not abort otherwise valid conversion after startup
- recovered table HTML is sanitized before entering the normal renderer

If hostile-input paths are untouched, say so rather than manufacturing a finding.

## Pass 3 — leafmd contracts

Flag diffs that:

- import `ebooklib` outside `leafmd.parse.ebooklib_adapter` or use `book.toc` as truth
- replace explicit `src-*` anchors with heading slugs
- write raw EPUB fragments into `toc.json`/`toc.md`
- join hrefs without preserving fragments or bypass `TargetMap`
- change planner merge/split defaults without focused regression coverage
- make `convert` implicitly run/alter `validate` without an explicit CLI/output-contract decision
- add Paddle/PaddleOCR as a leafmd runtime dependency rather than using the analyzer boundary
- convert source MathML to LaTeX (OCR-derived raster formulas are a separate opt-in path)
- remove original image assets merely because an occurrence was semantically replaced
- treat canonical Markdown/raw HTML as safe public HTML

## Pass 4 — tests

- New behavior/bug fixes need focused tests.
- Assert stable issue codes, not only message substrings.
- Security-path changes need hostile synthetic fixtures for the affected boundary.
- Image-analysis tests should fake/mock the backend in default CI and cover preserve/replace/failure/context behavior.
- No network, model downloads, sleeps, home-directory writes, copyrighted EPUBs, private corpus data, or model caches.

## Pass 5 — comment shape

Each actionable comment should state severity, file/hunk, the defect, why it violates a current invariant, and a concrete fix. Avoid phase/ticket archaeology, style churn, generic framework requests, or speculative website/daemon work.

## After review

List blockers first, then must-fix, then should-fix. Omit nits unless they would fail configured tooling.
