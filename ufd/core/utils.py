"""Utility functions for unused function detection."""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from ufd.core.models import DecoratorInfo, FunctionInfo

logger = logging.getLogger(__name__)


def extract_functions(
    content: str,
    file_uri: str,
) -> list[FunctionInfo]:
    """
    Parse Python source code and extract only top-level (module-level) functions.
    Excludes class methods and nested functions. All indices are 0-based.
    The `start_char` points to the first letter of the function name.

    Args:
        content: Python source code
        file_uri: URI of the file being parsed
    """
    module = ast.parse(content, filename=file_uri, type_comments=True)
    functions: list[FunctionInfo] = []
    lines = content.splitlines()

    for node in module.body:  # only top-level statements
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            line_idx = node.lineno - 1
            line = lines[line_idx]

            # Find the function name manually
            # Works for both `def` and `async def`
            def_pos = line.find("def ")
            async_pos = line.find("async def ")
            if async_pos != -1:
                name_start = async_pos + len("async def ")
            elif def_pos != -1:
                name_start = def_pos + len("def ")
            else:
                name_start = node.col_offset  # fallback

            # Extract decorators
            decorators = []
            if hasattr(node, "decorator_list") and node.decorator_list:
                for decorator in node.decorator_list:
                    decorator_name = _extract_decorator_name(decorator)
                    decorators.append(
                        DecoratorInfo(
                            name=decorator_name,
                            start_line=decorator.lineno - 1,
                            start_char=decorator.col_offset,
                        )
                    )

            functions.append(
                FunctionInfo(
                    file_uri=file_uri,
                    name=node.name,
                    start_line=line_idx,
                    start_char=name_start,
                    decorators=decorators,
                )
            )

    return functions


def _extract_decorator_name(decorator: ast.expr) -> str:
    """
    Extract the name of a decorator from AST node.

    Args:
        decorator: AST decorator node

    Returns:
        String representation of the decorator name
    """
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Attribute):
        # Handle cases like @app.get or @router.post
        parts = []
        node = decorator
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))
    if isinstance(decorator, ast.Call):
        # Handle cases like @app.get("/path")
        return _extract_decorator_name(decorator.func)
    return "unknown"


def iter_python_files(root: Path, include_tests: bool = False) -> list[Path]:
    """Recursively collect Python files, skipping typical ignored directories."""
    ignored_dirs = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "alembic",
        "migrations",
        "node_modules",
    }

    if not include_tests:
        ignored_dirs.update({"tests", "test", "testing"})

    return [p for p in root.rglob("*.py") if not any(part in ignored_dirs for part in p.parts)]
