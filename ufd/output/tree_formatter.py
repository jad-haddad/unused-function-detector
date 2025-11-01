"""Tree formatter for rich terminal output."""

from collections import defaultdict
from pathlib import Path

import rich
from rich.text import Text
from rich.tree import Tree

from ufd.core.models import ScanResult
from ufd.output.formatters import BaseFormatter

console = rich.console.Console()


class TreeFormatter(BaseFormatter):
    """Format results as a rich tree for terminal output."""

    def format(self, result: ScanResult) -> str:
        """Format scan results as a rich tree."""
        if not result.unused_functions:
            return "✅ No unused functions found!"

        # Print tree directly to console
        self._print_tree(result)
        return ""  # Return empty string since we printed directly

    def _print_tree(self, result: ScanResult) -> None:
        """Print the tree structure to console."""
        functions = result.unused_functions

        funcs_by_file = defaultdict(list)
        for func in functions:
            funcs_by_file[func.file_uri].append(func)

        root_tree = Tree(
            f"🔍 Unused functions by file (total {len(functions)} functions)",
            guide_style="dim",
        )

        dir_nodes: dict[tuple[str, ...], Tree] = {(): root_tree}

        for file_uri in sorted(funcs_by_file.keys()):
            file_funcs = funcs_by_file[file_uri]
            file_funcs.sort(key=lambda f: (f.start_line, f.start_char))

            raw = file_uri.removeprefix("file://")
            p = Path(raw)
            try:
                rel = p.relative_to(Path.cwd())
            except ValueError:
                rel = p

            parts = rel.parts
            if not parts:
                continue

            parent_key: tuple[str, ...] = ()
            parent_node: Tree = root_tree
            for part in parts[:-1]:
                key = (*parent_key, part)
                if key not in dir_nodes:
                    # Folder node (with trailing slash)
                    parent_node = parent_node.add(
                        f"[bold blue]{part}/[/bold blue]", guide_style="dim"
                    )
                    dir_nodes[key] = parent_node
                else:
                    parent_node = dir_nodes[key]
                parent_key = key

            file_name = parts[-1]
            file_node = parent_node.add(f"[bold green]{file_name}[/bold green]", guide_style="dim")

            for func in file_funcs:
                line_info = f"(line {func.start_line + 1})"
                func_text = Text(f"{func.name} ", style="magenta")
                func_text.append(line_info, style="grey50")
                file_node.add(func_text)

        console.print(root_tree)

        # Print summary
        console.print("\n📊 Summary:")
        console.print(f"   Files scanned: {result.files_scanned}")
        console.print(f"   Unused functions: {len(functions)}")
        console.print(f"   Scan duration: {result.scan_duration:.2f}s")
