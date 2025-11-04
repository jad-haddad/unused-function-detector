"""Protocol for LSP client."""

from typing import Any, Protocol


class ProgressCallback(Protocol):
    """Protocol defining a progress callback function."""

    def update(self, message: str, **fields: Any) -> None:
        """Update progress with a message."""
        ...


class LSPClientProtocol(Protocol):
    """Protocol defining the LSP client interface needed by utils."""

    async def hover(
        self, text_document_uri: str, line0: int, char0: int
    ) -> dict[str, object] | None:
        """Get hover information for a position in a file."""
        ...
