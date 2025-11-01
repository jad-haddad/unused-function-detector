"""Data models for unused function detection."""

from pydantic import BaseModel, Field


class DecoratorInfo(BaseModel):
    """Information about a function decorator."""

    name: str
    start_line: int
    start_char: int


class FunctionInfo(BaseModel):
    """Information about a function found in code."""

    file_uri: str
    name: str
    start_line: int
    start_char: int
    decorators: list[DecoratorInfo] = Field(default_factory=list)


class ScanResult(BaseModel):
    """Results of scanning for unused functions."""

    total_functions: int
    unused_functions: list[FunctionInfo]
    files_scanned: int
    scan_duration: float
