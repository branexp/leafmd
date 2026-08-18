# GitHub / PR workflow

Repository: [`branexp/leafmd`](https://github.com/branexp/leafmd) (public)

## Default flow

1. Update local `main` from `origin/main`.
2. Create one focused branch for the change.
3. Run focused tests while developing, then the CI-equivalent quality gate.
4. Open a PR into `main` with a concise scope and verification notes.
5. Wait for CI and review.
6. **Squash merge** and delete the branch.

Do not force-push shared branches or rewrite published history. Releases/PyPI publishing are not part of the normal PR workflow; add them only as explicit release work.

## Branch naming

Use short intent-based names. Recommended prefixes:

| Prefix | Use |
|---|---|
| `fix/<slug>` | Bug or correctness fix |
| `feat/<slug>` | New behavior |
| `test/<slug>` | Fixtures, regression tests, or characterization |
| `docs/<slug>` | Documentation only |
| `chore/<slug>` | CI, tooling, or repository hygiene |

Examples: `fix/toc-anchor-resolution`, `feat/image-recovery`, `docs/current-cli`.

## Local commands

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c docs/current-docs

# work, then run the CI-equivalent gate:
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run python -m pytest -m "not online and not private and not differential and not epubcheck"

git status
git add -A
git commit -m "docs: synchronize documentation with current behavior"
git push -u origin HEAD
gh pr create --repo branexp/leafmd
```

Merge after review/CI:

```bash
gh pr merge <n> --repo branexp/leafmd --squash --delete-branch
git switch main
git pull --ff-only origin main
```

## PR scope and release metadata

Keep PRs reviewable and avoid unrelated cleanup. A PR body should state what changed, what intentionally did not change, and the commands/selectors used to verify it.

Behavior or public-CLI changes should add an entry to `CHANGELOG.md` under `Unreleased`. A release PR must keep the versions in `pyproject.toml` and `src/leafmd/__init__.py` identical. Docs-only/test-only changes do not need a version bump unless they are part of a release.

## What must never be committed

- Copyrighted EPUBs or converted personal-library trees
- `.venv/`, `.mypy_cache/`, `.ruff_cache/`, generated `*.egg-info/`
- `.corpus/`, `private-corpus/`, or anything under `LEAFMD_CORPUS`
- Secrets, tokens, model caches, or local machine state

Synthetic EPUB fixtures belong under `tests/`.

## CI

`.github/workflows/ci.yml` runs on pushes to `main` and on pull requests. The matrix covers Python 3.11 and 3.12 and runs:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run python -m pytest -m "not online and not private and not differential and not epubcheck"
```

Default CI must remain deterministic and must not require network access, a private corpus, Docker EPUBCheck, or a live PaddleOCR/model installation.

## Copilot code review

Repository review guidance lives in:

- `.github/copilot-instructions.md` — repo-wide invariants
- `.github/instructions/python.instructions.md` — Python-specific rules
- `.github/instructions/tests.instructions.md` — test/fixture rules
- `.github/instructions/docs.instructions.md` — documentation rules
- `.github/skills/code-review/SKILL.md` — review procedure

Those files should describe current code and security boundaries, not historical phase/ticket plans.
