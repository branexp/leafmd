---
applyTo: "**/*.py"
---

# Python review (src + tests)

## Stack

- Python 3.11+, typed, `mypy --strict` on `leafmd`
- Lint/format: ruff (`E,F,I,B,UP`), line length 120
- CLI: Typer + Rich. Flags only. No config file.
- XML/HTML: lxml. Markdown: markdownify via `LeafmdConverter`
- Public types live in `leafmd.model`

## Architecture

- Keep `convert.py` a thin orchestrator.
- New parse/transform/render logic belongs in the existing package, not new top-level modules, unless the ticket says otherwise.
- Do not import `ebooklib` outside `leafmd.parse.ebooklib_adapter`.
- Prefer small typed functions over new abstract class hierarchies.
- Do not add Pydantic, Pandoc, tox/nox, or runtime network clients.

```python
# Avoid — leaks EbookLib above the adapter
from ebooklib import epub
toc = book.toc

# Prefer — adapter is a cross-check only
from leafmd.parse.ebooklib_adapter import cross_check_spine
```

## Types and errors

- Annotate public functions. Do not widen `local_name` / lxml tag types back to `str` only; comments and entity nodes happen.
- Fatal user/input failures: `FatalConversionError` with a stable code.
- Recoverable problems: `report.add(severity, CODE, message, where=...)`.
- Do not use bare `except:`. Narrow or `except Exception` with a report/continue and a reason.

## Links, paths, XML

- `posix_join` must preserve `#fragments`.
- Resolve internal hrefs through `TargetMap`. Do not concatenate paths by hand in writer/TOC code.
- `posix_norm` must strip traversal. Output paths stay inside the book directory.

## What not to nits

- Do not demand docstrings on every private helper.
- Do not restyle working code to Black/88 or require `any` purges that fight lxml.
- Do not suggest adding a config file, logger framework, or plugin system.
