"""JSON formatter for structured output."""

import json

from ufd.core.models import ScanResult
from ufd.output.formatters import BaseFormatter


class JsonFormatter(BaseFormatter):
    """Format results as JSON."""

    def format(self, result: ScanResult) -> str:
        """Format scan results as JSON."""
        data = {
            "summary": {
                "files_scanned": result.files_scanned,
                "total_functions": result.total_functions,
                "unused_functions_count": len(result.unused_functions),
                "scan_duration": result.scan_duration,
            },
            "unused_functions": [
                {
                    "file_uri": func.file_uri,
                    "name": func.name,
                    "line": func.start_line + 1,  # Convert to 1-based
                    "character": func.start_char,
                }
                for func in result.unused_functions
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
