"""Typer CLI for leafmd."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from leafmd import __version__
from leafmd.convert import convert_epub
from leafmd.errors import FatalConversionError, UsageError
from leafmd.inspect_cmd import inspect_epub
from leafmd.model.issues import IssueSeverity
from leafmd.model.report import ConversionReport
from leafmd.validate.output import validate_book_directory

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Compile EPUB 2/3 into Markdown book directories.")
console = Console()
err_console = Console(stderr=True)


@app.callback()
def main() -> None:
    """leafmd CLI."""
    return


@app.command("convert")
def convert_cmd(
    book: Path = typer.Argument(..., exists=True, readable=True, help="EPUB file"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output book directory"),
    strict: bool = typer.Option(False, "--strict", help="Promote selected warnings to errors"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print warnings"),
    debug: bool = typer.Option(False, "--debug", help="Print info/debug issues"),
) -> None:
    """Convert one EPUB into a canonical Markdown book directory."""
    try:
        book_dir, report = convert_epub(book, output, strict=strict)
    except FatalConversionError as exc:
        err_console.print(f"[red]fatal[/red] {exc.code}: {exc}")
        raise typer.Exit(code=2) from exc
    except UsageError as exc:
        err_console.print(f"[red]usage[/red] {exc}")
        raise typer.Exit(code=3) from exc

    _print_report(report, verbose=verbose, debug=debug)
    console.print(f"Wrote {book_dir}")
    raise typer.Exit(code=_exit_code(report))


@app.command("inspect")
def inspect_cmd(
    book: Path = typer.Argument(..., exists=True, readable=True),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output"),
) -> None:
    """Inspect EPUB metadata, spine, and navigation without writing output."""
    try:
        payload = inspect_epub(book)
    except FatalConversionError as exc:
        if as_json:
            console.print_json(data={"status": "fatal", "code": exc.code, "message": str(exc)})
        else:
            err_console.print(f"[red]fatal[/red] {exc.code}: {exc}")
        raise typer.Exit(code=2) from exc
    if as_json:
        console.print_json(data=payload)
    else:
        console.print(f"{payload['title']} ({payload['epub_version']})")
        if payload["authors"]:
            console.print("Authors: " + ", ".join(payload["authors"]))
        console.print(f"Package: {payload['package_path']}")
        console.print(f"Spine items: {len(payload['spine'])}")
        console.print(f"Nav entries: {len(payload['nav_toc'])}  NCX: {len(payload['ncx_toc'])}")
        if payload["issues"]:
            console.print(f"Issues: {len(payload['issues'])}")
    raise typer.Exit(code=2 if payload.get("status") == "fatal" else 0)


@app.command("validate")
def validate_cmd(
    book_dir: Path = typer.Argument(..., exists=True, file_okay=False, help="Generated book directory"),
    as_json: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Re-check a generated book directory."""
    report = validate_book_directory(book_dir)
    if as_json:
        console.print_json(data=report.to_dict())
    else:
        _print_report(report, verbose=verbose, debug=False)
        console.print(f"status: {report.status}")
    raise typer.Exit(code=_exit_code(report))


@app.command("report")
def report_cmd(book_dir: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    """Print conversion-report.json from a book directory."""
    path = book_dir / "conversion-report.json"
    if not path.is_file():
        err_console.print(f"Missing {path}")
        raise typer.Exit(code=2)
    payload = json.loads(path.read_text(encoding="utf-8"))
    console.print_json(data=payload)


@app.command("version")
def version_cmd() -> None:
    """Print the leafmd version."""
    console.print(__version__)


def _print_report(report: ConversionReport, *, verbose: bool, debug: bool) -> None:
    visible = []
    for issue in report.issues:
        if issue.severity in {IssueSeverity.FATAL, IssueSeverity.ERROR}:
            visible.append(issue)
        elif issue.severity is IssueSeverity.WARNING and verbose:
            visible.append(issue)
        elif issue.severity in {IssueSeverity.INFO, IssueSeverity.DEBUG} and debug:
            visible.append(issue)
    if not visible:
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("sev")
    table.add_column("code")
    table.add_column("where")
    table.add_column("message")
    for issue in visible:
        table.add_row(issue.severity.value, issue.code, issue.where or "", issue.message)
    err_console.print(table)


def _exit_code(report: ConversionReport) -> int:
    if report.has_fatal() or report.status == "fatal":
        return 2
    if report.has_errors():
        return 1
    return 0
