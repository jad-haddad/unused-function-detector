"""Main unused function detector."""

import logging
import time
from pathlib import Path

from ufd.core.lsp_client import LSPClient
from ufd.core.models import FunctionInfo, ScanResult
from ufd.core.utils import extract_functions, has_framework_decorators, iter_python_files

logger = logging.getLogger(__name__)


class UnusedFunctionDetector:
    """Main class for detecting unused functions using LSP."""

    def __init__(
        self,
        lsp_server_cmd: list[str],
        verbose: bool = False,
    ) -> None:
        self.verbose = verbose
        self.lsp_server_cmd = lsp_server_cmd

        logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    async def scan(
        self,
        path: Path,
        include_tests: bool = False,
        include_private: bool = False,
    ) -> ScanResult:
        """
        Scan a path for unused functions.

        Args:
            path: Path to scan
            include_tests: Whether to include test files
            include_private: Whether to include private functions (starting with _)
            include_fastapi: Whether to include FastAPI route functions

        Returns:
            ScanResult with unused functions found
        """
        start_time = time.time()

        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")

        # Get all Python files to scan
        files = iter_python_files(path, include_tests=include_tests)

        logger.debug(f"Found {len(files)} Python files to scan")

        unused_functions, total_functions = await self._scan_files(files, include_private, path)

        scan_duration = time.time() - start_time

        return ScanResult(
            total_functions=total_functions,
            unused_functions=unused_functions,
            files_scanned=len(files),
            scan_duration=scan_duration,
        )

    async def _scan_files(
        self,
        files: list[Path],
        include_private: bool,
        root_path: Path,
    ) -> tuple[list[FunctionInfo], int]:
        """Scan files for unused functions using LSP."""
        client = LSPClient(server_cmd=self.lsp_server_cmd)
        unused_functions: list[FunctionInfo] = []
        total_functions = 0

        try:
            await client.connect()
            root_uri = root_path.resolve().as_uri()
            await client.initialize(root_uri)

            # Configure LSP server
            await client.notify(
                "workspace/didChangeConfiguration",
                params={
                    "settings": {
                        "python": {
                            "analysis": {
                                "typeCheckingMode": "off",
                                "diagnosticMode": "workspace",
                            }
                        }
                    }
                },
            )

            # Wait for initial analysis to complete
            logger.debug("Waiting for LSP analysis to complete...")
            await client.wait_for_analysis_complete()

            # Process files sequentially like the old version
            for file_path in files:
                logger.debug(f"Processing {file_path}")

                try:
                    uri = file_path.resolve().as_uri()
                    content = file_path.read_text(encoding="utf-8")

                    funcs_in_file = extract_functions(content, uri)

                    # Filter private functions if requested
                    if not include_private:
                        funcs_in_file = [f for f in funcs_in_file if not f.name.startswith("_")]

                    total_functions += len(funcs_in_file)

                    # Check references for each function immediately
                    for func in funcs_in_file:
                        logger.debug(f"Checking references for {func.name} in {func.file_uri}")

                        try:
                            # Check if function has framework decorators that should be excluded
                            if await has_framework_decorators(func, client):
                                logger.debug(f"Skipping {func.name} - has framework decorators")
                                continue

                            result = await client.references(
                                text_document_uri=func.file_uri,
                                line0=func.start_line,
                                char0=func.start_char,
                            )

                            if not result:
                                unused_functions.append(func)

                        except Exception as e:
                            logger.warning(f"Failed to check references for {func.name}: {e}")

                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")

        finally:
            await client.shutdown()

        logger.debug(f"Found {len(unused_functions)} unused functions out of {total_functions}")

        return unused_functions, total_functions
