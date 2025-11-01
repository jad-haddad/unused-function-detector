"""
Unused Function Detector - Find unused functions in Python codebases using LSP.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from ufd.core.detector import UnusedFunctionDetector
from ufd.core.lsp_client import LSPClient

__all__ = ["LSPClient", "UnusedFunctionDetector"]
