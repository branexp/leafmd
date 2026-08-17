# GitHub / PR workflow

Private repo: [`branexp/leafmd`](https://github.com/branexp/leafmd)

Local path: `/home/clawdbot/clawd/projects/leafmd`

This folder is **not** part of `giga-workspace`. `~/clawd/.gitignore` ignores `/projects/`. Treat leafmd as its own git root.

## Frozen process

House style, same as other `branexp` repos:

1. Branch off `main`.
2. Open a PR into `main`.
3. Wait for CI (`ruff`, `mypy`, `pytest` on 3.11 and 3.12).
4. Review, then **squash merge**.
5. Delete the branch.

Do not commit to `main` after the seed push except for emergency hotfix with Brandon's OK. Do not rewrite published history. Do not make the repo public. Do not publish to PyPI.

## What already landed on `main`

The repo was seeded with the Phase 1 tree and has since merged the first three implementation PRs:

- scaffolded converter / inspect / validate / report
- P1-0 quality-gate collection fix
- P1-1 fragment join, TOC/anchor rewrite, XXE `local_name` hardening, mypy cleanup
- this workflow + the implementation plan
- PR 1: Copilot review instructions
- PR 2: link, asset, and validator correctness
- PR 3: semantic reconstruction (cover discovery, evidence-ranked classification, planner B/C, and text cleanup)

The current Phase 4 work is on `feat/phase4-rich-content` and is intended to go out as one PR after local documentation and quality-gate review. The branch is still unpushed; do not infer merge status from local commits.

## Branch naming

One ticket per branch. Prefix by kind:

| Prefix | Use |
|---|---|
| `fix/<ticket>-<slug>` | Closeout bugs (P1-0 leftovers, P2-1, P2-3) |
| `feat/<ticket>-<slug>` | New behavior (P1-2 harness, P1-5 epubcheck, P2-2 assets) |
| `test/<ticket>-<slug>` | Fixtures / goldens / characterization only |
| `docs/<ticket>-<slug>` | Contract docs with no production code |
| `chore/<slug>` | CI, ignore rules, repo hygiene |

Examples:

- `test/p1-2-golden-harness`
- `test/p1-3-acceptance-fixtures`
- `docs/p1-4-contract-docs`
- `fix/p2-1-fragment-map`
- `feat/p2-2-assets`

Never put two §8 tickets on one branch unless the parent explicitly merges write-scopes.

## PR size and write-scope

Follow `docs/implementation-plan.md` §8.

- One ticket id in the title: `feat(P1-2): golden harness`
- Write only the files listed for that ticket.
- Parent owns architecture, format contract, security, goldens approval, planner B/C.
- Subagents stay isolated. No overlapping files across parallel PRs.

### Historical first-PR stack (traceability)

The following table records the original proposed stack. It is not the current queue; Phase 2 and Phase 3 were delivered as consolidated PRs, and the remaining Phase 1 closeout items are tracked in the implementation plan.

| Order | Ticket | Branch | Notes |
|---|---|---|---|
| 1 | P1-2 | `test/p1-2-golden-harness` | Harness + unapproved fixtures only. Do not bless goldens yet. |
| 2 | P1-3 | `test/p1-3-acceptance-fixtures` | New builders/tests. Can overlap timing with P1-4/P2-4 if files don't collide. |
| 3 | P1-4 | `docs/p1-4-contract-docs` | Docs only. |
| 4 | P2-4 | `test/p2-4-html5lib-spike` | Characterization. No runtime dep unless parent accepts. |
| 5 | P2-5 | `test/p2-5-planner-bc-fixtures` | Failing characterization tests only. |
| 6 | P2-1 | `fix/p2-1-fragment-map` | After P1-1 (already on main). Parent reviews invariant. |
| 7 | P2-2 | `feat/p2-2-assets` | Parallel with P2-1 if `transform/assets.py` only. |
| 8 | P2-3 | `fix/p2-3-validate-report` | After P2-1 contract. |
| 9 | P1-5 | `feat/p1-5-epubcheck` | Optional. Not an MVP blocker. |

Do **not** reopen the historical Phase 1–3 ticket stack. New work should use one focused branch/PR, preserve the canonical schema and anchor contract, and update the implementation plan when a phase changes.

## Local commands

```bash
cd /home/clawdbot/clawd/projects/leafmd
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c test/p1-2-golden-harness

# work, then:
ruff check src tests
ruff format --check src tests
mypy
python -m pytest

git add -A
git status   # confirm no .venv, egg-info, corpus, copyrighted EPUBs
git commit -m "test(P1-2): add golden harness without approving trees"
git push -u origin HEAD
gh pr create --repo branexp/leafmd --title "test(P1-2): golden harness" --body-file /tmp/leafmd-pr.md
```

PR body should include:

- Ticket id and write-scope
- Quality-gate commands run
- What is *not* in the PR
- How to verify (exact pytest selectors)

Merge:

```bash
gh pr merge <n> --repo branexp/leafmd --squash --delete-branch
git switch main
git pull --ff-only origin main
```

## Push rules

- Creating this remote and seeding `main` was explicitly requested.
- Later feature pushes are expected as part of the PR flow above.
- Still ask before: force-push, history rewrite, public visibility, PyPI, SWAG/DNS, or adding a second remote.
- Session wrap-up may push already-approved leafmd branches; do not silently push new work to `main`.

## What must never be committed

- Copyrighted EPUBs or converted personal library trees
- `.venv/`, `.mypy_cache/`, `.ruff_cache/`, `src/*.egg-info/`
- `.corpus/`, `private-corpus/`, anything under `LEAFMD_CORPUS`
- Secrets, tokens, host paths that aren't already in docs

`.gitignore` already covers the local caches and private corpus dirs. Keep it that way.

## CI

`.github/workflows/ci.yml` runs on push to `main` and on pull requests:

- Python 3.11 and 3.12
- `ruff check` + `ruff format --check`
- `mypy`
- `pytest`

CI must not update goldens. Golden refresh is an explicit local flag and a reviewed PR. Install uses a uv venv (not `--system`) because GitHub-hosted Ubuntu Python is externally managed.

## Copilot code review

PRs are reviewed with GitHub Copilot code review. Instructions are read from the **head branch**:

- `.github/copilot-instructions.md` — repo-wide invariants
- `.github/instructions/python.instructions.md` — `**/*.py`
- `.github/instructions/tests.instructions.md` — `tests/**`
- `.github/instructions/docs.instructions.md` — `docs/**/*.md`
- `.github/skills/code-review/SKILL.md` — review procedure (directory name `code-review` so Copilot code review loads it)

Keep those files short and imperative. Do not move product rules behind a link Copilot will not follow. Request Copilot as a reviewer on every PR; turn on automatic reviews + “Review new pushes” in repo settings if available.

## Shipping trace

After squash-merge:

1. Update `docs/implementation-plan.md` ticket status if the parent is doing closeout.
2. Flatnotes `PJT leafmd - 90 Log` when that note exists.
3. Do not also commit leafmd into `giga-workspace`.
