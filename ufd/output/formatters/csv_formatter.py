"""CSV formatter for spreadsheet-compatible output."""

import csv
from io import StringIO

from ufd.core.models import ScanResult
from ufd.output.formatters.protocols import BaseFormatter


class CsvFormatter(BaseFormatter):
    """Format results as CSV."""

    def format(self, result: ScanResult) -> str:
        """Format scan results as CSV."""
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["File", "Function", "Line", "Character"])

        # Write data
        for func in result.unused_functions:
            # Convert file URI to relative path
            file_path = func.file_uri.removeprefix("file://")
            writer.writerow(
                [
                    file_path,
                    func.name,
                    func.start_line + 1,  # Convert to 1-based
                    func.start_char,
                ]
            )

        return output.getvalue()
