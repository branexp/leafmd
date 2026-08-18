---
applyTo: "**/*.py"
---

# Python review (src + tests)

## Stack

- Python 3.11+, typed, `mypy --strict` on `leafmd`
- Lint/format: ruff (`E,F,I,B,UP`), line length 120
- CLI: Typer + Rich; flags only, no config file
- XML/HTML: lxml; Markdown: markdownify via `LeafmdConverter`
- Public conversion/report/publication types live in `leafmd.model`

## Architecture

- Keep `convert.py` a thin orchestrator.
- Put parsing, semantics, image analysis/replacement, transforms, rendering, and validation in their existing packages rather than growing top-level orchestration.
- Do not import `ebooklib` outside `leafmd.parse.ebooklib_adapter`.
- `leafmd.images.ImageAnalyzer` is the optional backend boundary. Do not add Paddle/PaddleOCR as a leafmd runtime dependency; the built-in adapter shells out to an explicit external executable.
- Keep image replacement before normal link/asset rewriting and preserve original copied assets.
- Keep `validate` independent from `convert` unless a deliberate public contract change says otherwise.
- Prefer small typed functions over new abstract class hierarchies.
- Do not add Pydantic, Pandoc, tox/nox, or core runtime network clients.

```python
# Avoid — leaks EbookLib above the adapter
from ebooklib import epub
toc = book.toc

# Prefer — direct parsing is truth; EbookLib stays behind the adapter
from leafmd.parse.ebooklib_adapter import load_publication
```

## Types and errors

- Annotate public functions. Do not narrow `local_name` / lxml tag types back to `str` only; comments and entity nodes occur.
- Fatal input failures: `FatalConversionError` with a stable code.
- CLI/application configuration failures: `UsageError` (exit 3 in `convert`).
- Recoverable conversion problems: `report.add(severity, CODE, message, where=...)`.
- Do not use bare `except:`. Narrow exceptions, or use `except Exception` only at an intentional fail-open boundary with reporting.

## Links, paths, XML, external tools

- `posix_join` must preserve `#fragments`.
- Resolve internal hrefs through `TargetMap`; do not hand-build TOC/content destinations.
- Keep generated paths inside the book directory and retain validator escape checks.
- XML entity resolution/DTD/network access must remain disabled.
- External analyzers must be opt-in, bounded to local staged inputs, and fail open to preserved source content after successful configuration.

## What not to nit

- Do not demand docstrings on every private helper.
- Do not restyle working code to Black/88 or require type purges that fight lxml.
- Do not suggest adding a config file, logger framework, or plugin system without a concrete product need.
