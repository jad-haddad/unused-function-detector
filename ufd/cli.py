"""CLI interface for unused function detector."""

import asyncio
import logging
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
)

from ufd.core.detector import UnusedFunctionDetector
from ufd.core.protocols import ProgressCallback
from ufd.output.formatters.enums import OutputFormat
from ufd.output.formatters.formatter_factory import get_formatter

app = typer.Typer(
    name="ufd",
    help="🔍 Find unused functions in Python codebases using LSP",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()

DEFAULT_PATH = Path(".")


class RichProgressCallback(ProgressCallback):
    def __init__(self, progress: Progress, task_id: TaskID) -> None:
        self.progress = progress
        self.task_id = task_id

    def update(self, message: str, **fields: Any) -> None:
        self.progress.update(self.task_id, description=message, **fields)


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
        MofNCompleteColumn(),
        BarColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task("Scanning for unused functions...", total=None)
        progress_callback = RichProgressCallback(progress, task_id)

        try:
            result = asyncio.run(
                detector.scan(
                    path=path,
                    include_tests=include_tests,
                    include_private=include_private,
                    progress_callback=progress_callback,
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
            f"[yellow]⚠️  Found {len(result.unused_functions)} unused function(s)[/yellow]"
        )
        raise typer.Exit(1)
    console.print("[green]✅ No unused functions found![/green]")


@app.command("version")
def cli_version() -> None:
    """Show version information."""
    try:
        console.print(version("unused-function-detector"))
    except PackageNotFoundError:
        console.print("unknown")


@app.command()
def doctor() -> None:
    """Check system requirements and setup."""
    console.print("🔧 Checking system requirements...")

    python_version = sys.version_info
    if python_version >= (3, 10):
        console.print(f"[green]✓ Python {python_version.major}.{python_version.minor}[/green]")
    else:
        console.print(
            f"[red]✗ Python {python_version.major}.{python_version.minor} (requires 3.10+)[/red]"
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
