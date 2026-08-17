---
applyTo: "docs/**/*.md"
---

# Docs review

## Sources of truth

- Frozen product decisions: `docs/implementation-plan.md` §2
- PR process: `docs/github-workflow.md`
- Do not silently reopen §2 (name, privacy, regenerate-only, case A planner, anchor contract, schemes, AGPL).

## Writing rules

- Document **current** shipped behavior. Label unshipped footnotes, html5lib, EPUBCheck, and the reading site as later. Phase 3 B/C may be documented once the matching P3 ticket lands.
- Do not promise a public API, PyPI release, daemon, or `book.pettee.org` implementation in this repo.
- Keep commands copy-pasteable and matching CI: `ruff`, `mypy`, `python -m pytest`.
- Prefer short imperative lists over architecture essays.

## What to flag

- Docs that describe unimplemented Phase 3–6 behavior as if it shipped
- Instructions that tell people to commit EPUBs or converted libraries
- Broken relative links between docs
- Security claims that the converter output is safe public HTML
