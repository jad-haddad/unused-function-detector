"""Base formatter interface for output formatting."""

from pathlib import Path
from typing import Protocol

from ufd.core.models import ScanResult


class BaseFormatter(Protocol):
    """Base class for output formatters."""

    def format(self, result: ScanResult) -> str:
        """Format the scan result into a string."""
        ...

    def save(self, result: ScanResult, output_file: Path) -> None:
        """Save formatted result to a file."""
        content = self.format(result)
        output_file.write_text(content, encoding="utf-8")
