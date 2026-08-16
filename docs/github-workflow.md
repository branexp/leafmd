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

The empty GitHub repo was seeded with the current Phase 1 tree, including:

- scaffolded converter / inspect / validate / report
- P1-0 quality-gate collection fix
- P1-1 fragment join, TOC/anchor rewrite, XXE `local_name` hardening, mypy cleanup
- this workflow + the implementation plan

That seed is **not** MVP acceptance. Later tickets still go out as PRs.

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

Suggested first PR stack (after seed):

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

Do **not** start Phase 3 implementation PRs until P1-0…P1-5 and P2-1 pass.

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

CI must not update goldens. Golden refresh is an explicit local flag and a reviewed PR.

## Shipping trace

After squash-merge:

1. Update `docs/implementation-plan.md` ticket status if the parent is doing closeout.
2. Flatnotes `PJT leafmd - 90 Log` when that note exists.
3. Do not also commit leafmd into `giga-workspace`.
