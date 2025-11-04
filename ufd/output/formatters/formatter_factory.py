from ufd.output.formatters.csv_formatter import CsvFormatter
from ufd.output.formatters.enums import OutputFormat
from ufd.output.formatters.json_formatter import JsonFormatter
from ufd.output.formatters.protocols import BaseFormatter
from ufd.output.formatters.tree_formatter import TreeFormatter


def get_formatter(output_format: OutputFormat) -> BaseFormatter:
    """Get the appropriate formatter for the output format."""
    formatters = {
        OutputFormat.TREE: TreeFormatter(),
        OutputFormat.JSON: JsonFormatter(),
        OutputFormat.CSV: CsvFormatter(),
    }

    return formatters[output_format]
