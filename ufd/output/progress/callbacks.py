from typing import Any

from rich.progress import Progress, TaskID

from ufd.output.progress.protocols import ProgressCallback


class RichProgressCallback(ProgressCallback):
    def __init__(self, progress: Progress, task_id: TaskID) -> None:
        self.progress = progress
        self.task_id = task_id

    def update(self, message: str, **fields: Any) -> None:
        self.progress.update(self.task_id, description=message, **fields)


class NoOpProgressCallback(ProgressCallback):
    """No-op progress callback implementation."""

    def update(self, message: str, **fields: Any) -> None:
        pass
