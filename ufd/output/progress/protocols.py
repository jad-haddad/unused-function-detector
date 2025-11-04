from typing import Any, Protocol


class ProgressCallback(Protocol):
    """Protocol defining a progress callback function."""

    def update(self, message: str, **fields: Any) -> None:
        """Update progress with a message."""
        ...
