---
name: code-review
description: "Review leafmd pull requests for hostile-EPUB safety, parser/anchor contracts, write-scope, and missing tests. Use for Copilot code review and any PR review of this repository."
---

# leafmd code review

Use this skill on every leafmd pull request. Directory name is `code-review` so Copilot code review loads it.

Custom instructions hold standing rules. This skill is the **review procedure**. Do not restate the whole product spec.

Read first, in this order:

1. PR title and body (ticket id, write-scope, “not in this PR”)
2. Diff only, plus nearby call sites you must understand
3. `.github/copilot-instructions.md`
4. Matching `.github/instructions/*.instructions.md` for touched paths
5. `docs/implementation-plan.md` §2 only if an invariant is in dispute

Do not follow links to Flatnotes or off-repo docs. If a rule is not in this repo, do not invent it.

## Severity

Use these labels in comments. Do not try to block merge.

- **Blocker:** security hole, DRM bypass, network I/O, zip-slip, XXE/DTD, raw EPUB ids in TOC, EbookLib import above the adapter, copyrighted EPUB committed, output path escape
- **Must-fix:** broken Phase 1 contract (case A planner, missing `src-…` anchors, `posix_join` dropping fragments, dropped `linear="no"`, missing report code, CI-breaking types)
- **Should-fix:** missing regression test, write-scope leak, unstable assertion on message text, golden update mixed into a behavior PR
- **Nit:** style only if ruff/mypy would fail. Skip taste nits.

If nothing rises to should-fix or above, say so in one short summary. Do not pad.

## Pass 1 — scope and intent

- Confirm one §8 ticket (or an explicit hygiene PR). Flag unrelated file churn.
- Production PRs should not silently rewrite goldens, planner B/C, site/SWAG, or PyPI.
- Docs-only PRs should not change `src/`.
- Test-only PRs may add failing characterization tests. Do not “fix” them by implementing Phase 3.

## Pass 2 — hostile input

On any ingest/parse/transform/validate change, look for:

- zip-slip (`..`, absolute, backslash, drive letter)
- bomb limits bypassed or raised without justification
- `encryption.xml` / DRM accepted
- XML entity resolution, network, or DTD enabled
- `script` / `iframe` / `object` / `embed` / `form` / `on*` surviving rewrite
- unsafe URL schemes kept
- SVG script, event attrs, or external http refs
- remote asset fetch
- book-dir path escape in writer or validator

No finding is not a skip. Say “hostile-input paths unchanged” if the diff does not touch them.

## Pass 3 — leafmd contracts

Flag if the diff:

- imports `ebooklib` outside `leafmd.parse.ebooklib_adapter`
- uses `book.toc` as truth
- implements in-file split or multi-file merge without a Phase 3 ticket
- emits heading slugs instead of `<a id="src-<stem>-<id>"></a>`
- writes original EPUB fragment ids into `toc.json` / `toc.md`
- joins hrefs without preserving `#fragment`
- concatenates TOC/output paths instead of using `TargetMap`
- fetches or downloads anything during convert/inspect/validate
- treats converter Markdown as safe public HTML

## Pass 4 — tests

- New behavior or bug fix needs a test.
- Assert issue **codes**, not message substrings.
- Security-path changes need a hostile fixture.
- Goldens: no `--update-goldens` in CI; no blessing trees in the same PR as output changes unless the ticket is a golden update.
- No network, no sleeps, no home-directory writes, no copyrighted EPUBs.

## Pass 5 — comment shape

Each comment:

1. Severity
2. File/hunk
3. What is wrong (one sentence)
4. Why it matters for leafmd (invariant or security)
5. Concrete fix, with a tiny patch if obvious

Do not:

- Relitigate §2 frozen decisions
- Ask for a website, daemon, config file, or plugin system
- Demand docstrings on every private helper
- Restyle to Black/88
- Change Copilot comment formatting or the PR overview
- Approve or request-changes (Copilot comments only)

## After review

If you used this skill, say so in the summary (“used code-review skill”). List blockers first, then must-fix, then should-fix. Omit nits unless the file is otherwise clean and the nit would fail CI.
