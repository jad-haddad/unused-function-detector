"""LSP-specific utility functions for unused function detection."""

import logging

from ufd.core.models import DecoratorInfo, FunctionInfo
from ufd.core.protocols import LSPClientProtocol

logger = logging.getLogger(__name__)


async def check_decorator_types(
    decorators: list[DecoratorInfo], file_uri: str, lsp_client: LSPClientProtocol
) -> dict[str, bool]:
    """
    Check the types of decorators using LSP hover to identify framework decorators.

    Args:
        decorators: List of decorator information
        file_uri: URI of the file being analyzed
        lsp_client: LSP client for hover requests

    Returns:
        Dictionary mapping decorator names to whether they are framework decorators
    """
    decorator_types = {}

    for decorator in decorators:
        try:
            # Get hover information for the decorator
            hover_result = await lsp_client.hover(
                file_uri, decorator.start_line, decorator.start_char
            )

            if not hover_result or not hover_result.get("contents"):
                decorator_types[decorator.name] = False
                continue

            # Extract the hover content
            contents = hover_result["contents"]
            if isinstance(contents, dict) and "value" in contents:
                hover_text = contents["value"]
            elif isinstance(contents, list):
                hover_text = " ".join(str(item) for item in contents)
            else:
                hover_text = str(contents)

            # Check if hover text indicates a framework decorator
            decorator_types[decorator.name] = is_framework_decorator(hover_text)

        except Exception as e:
            logger.debug(f"Failed to check decorator {decorator.name} via LSP hover: {e}")
            decorator_types[decorator.name] = False

    return decorator_types


def is_framework_decorator(hover_text: str) -> bool:
    hover_text_lower = hover_text.lower()

    # Framework-specific type indicators
    framework_indicators = [
        "apirouter",  # FastAPI
        "fastapi",  # FastAPI
        "typer",  # Typer CLI
        "click",  # Click CLI
        "command",  # Generic command decorators
    ]

    # Check if any framework indicators are present
    return any(indicator in hover_text_lower for indicator in framework_indicators)


async def has_framework_decorators(func: FunctionInfo, lsp_client: LSPClientProtocol) -> bool:
    if not func.decorators:
        return False

    decorator_types = await check_decorator_types(func.decorators, func.file_uri, lsp_client)

    # Check if any decorator is a framework decorator
    return any(is_framework for _, is_framework in decorator_types.items())
