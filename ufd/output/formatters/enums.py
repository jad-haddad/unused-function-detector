from enum import Enum


class OutputFormat(str, Enum):
    TREE = "tree"
    JSON = "json"
    CSV = "csv"
