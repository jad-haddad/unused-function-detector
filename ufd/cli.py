"""CLI interface for unused function detector using Typer."""

import asyncio
import logging
import shutil
import sys
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ufd.core.detector import UnusedFunctionDetector
from ufd.output.csv_formatter import CsvFormatter
from ufd.output.formatters import BaseFormatter
from ufd.output.json_formatter import JsonFormatter
from ufd.output.tree_formatter import TreeFormatter


class OutputFormat(StrEnum):
    TREE = "tree"
    JSON = "json"
    CSV = "csv"


app = typer.Typer(
    name="ufd",
    help="🔍 Find unused functions in Python codebases using LSP",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()

DEFAULT_PATH = Path(".")


def get_formatter(output_format: OutputFormat) -> BaseFormatter:
    """Get the appropriate formatter for the output format."""
    formatters = {
        OutputFormat.TREE: TreeFormatter(),
        OutputFormat.JSON: JsonFormatter(),
        OutputFormat.CSV: CsvFormatter(),
    }

    return formatters[output_format]


@app.command()
def check(
    path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            help="Path to scan for unused functions",
        ),
    ] = DEFAULT_PATH,
    include_tests: Annotated[
        bool,
        typer.Option(
            "--include-tests",
            help="Include test files in analysis",
        ),
    ] = False,
    include_private: Annotated[
        bool,
        typer.Option(
            "--include-private",
            "-p",
            help="Include private functions (starting with _)",
        ),
    ] = False,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--output",
            "-o",
            help="Output format: tree, json, csv",
        ),
    ] = OutputFormat.TREE,
    output_file: Annotated[
        Path | None,
        typer.Option(
            "--output-file",
            "-f",
            help="Save results to file",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Verbose output",
        ),
    ] = False,
) -> None:
    """
    Scan Python codebase for unused functions.

    This tool uses Language Server Protocol (LSP) to accurately detect
    functions that are never referenced in your codebase.

    Examples:
        ufd ./my-project
        ufd --include-tests --output json
        ufd -p -o csv -f results.csv
        ufd --include-fastapi  # include FastAPI routes in analysis
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    lsp_server = ["basedpyright-langserver", "--stdio"]

    detector = UnusedFunctionDetector(
        verbose=verbose,
        lsp_server_cmd=lsp_server,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        _ = progress.add_task("Scanning for unused functions...", total=None)

        try:
            result = asyncio.run(
                detector.scan(
                    path=path,
                    include_tests=include_tests,
                    include_private=include_private,
                )
            )
        except Exception as e:
            console.print(f"[red]Error during scan: {e}[/red]")
            if verbose:
                console.print_exception()
            raise typer.Exit(1)

    formatter = get_formatter(output_format)

    if output_format == "tree":
        formatter.format(result)
    else:
        output = formatter.format(result)

        if output_file:
            _ = output_file.write_text(output, encoding="utf-8")
            console.print(f"[green]Results saved to {output_file}[/green]")
        else:
            console.print(output)

    if result.unused_functions:
        console.print(
            f"\n[yellow]⚠️  Found {len(result.unused_functions)} unused function(s)[/yellow]"
        )
        raise typer.Exit(1)
    console.print("\n[green]✅ No unused functions found![/green]")


@app.command()
def version() -> None:
    """Show version information."""
    console.print("ufd v0.1.0")


@app.command()
def doctor() -> None:
    """Check system requirements and setup."""
    console.print("🔧 Checking system requirements...")

    python_version = sys.version_info
    if python_version >= (3, 8):
        console.print(f"[green]✓ Python {python_version.major}.{python_version.minor}[/green]")
    else:
        console.print(
            f"[red]✗ Python {python_version.major}.{python_version.minor} (requires 3.8+)[/red]"
        )
        raise typer.Exit(1)

    lsp_server = shutil.which("basedpyright-langserver")
    if lsp_server:
        console.print(f"[green]✓ basedpyright-langserver found at {lsp_server}[/green]")
    else:
        console.print("[yellow]⚠ basedpyright-langserver not found[/yellow]")
        console.print("Install with: pip install basedpyright")

    console.print("\n[green]✓ System check complete[/green]")


if __name__ == "__main__":
    app()
