import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class AsyncStdioTransport:
    """Handles JSON-RPC transport for LSP communication."""

    def __init__(self, proc: asyncio.subprocess.Process) -> None:
        self.proc = proc
        self._buffer: bytes = b""
        self._stderr_task: asyncio.Task[None] | None = None

    async def send(self, payload: dict[str, Any]) -> None:
        """Send a JSON-RPC payload to the LSP server."""
        if self.proc.stdin is None:
            raise RuntimeError("Stdin is closed")
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        self.proc.stdin.write(header + body)
        await self.proc.stdin.drain()

    async def read_message(self) -> dict[str, Any] | None:
        """Reads one LSP message from stdout."""
        while True:
            header_end = self._buffer.find(b"\r\n\r\n")
            if header_end != -1:
                header = self._buffer[:header_end].decode("ascii", errors="replace")
                rest = self._buffer[header_end + 4 :]
                content_length = None
                for line in header.split("\r\n"):
                    if line.lower().startswith("content-length:"):
                        try:
                            content_length = int(line.split(":", 1)[1].strip())
                        except ValueError:
                            pass
                        break

                if content_length is None:
                    self._buffer = rest  # Discard invalid header
                    continue

                if len(rest) >= content_length:
                    body = rest[:content_length]
                    self._buffer = rest[content_length:]
                    try:
                        return json.loads(body.decode("utf-8"))
                    except json.JSONDecodeError:
                        logger.debug("Failed to parse JSON body from LSP server")
                        continue

            # Read more data
            assert self.proc.stdout is not None
            data = await self.proc.stdout.read(4096)
            if not data:
                return None
            self._buffer += data

    async def close(self) -> None:
        """Close the transport and cleanup."""
        if self.proc.stdin is not None:
            self.proc.stdin.close()
        await self.proc.wait()
        if self.proc.returncode is None:
            self.proc.terminate()


class LSPClient:
    """Simple JSON-RPC client for Language Server Protocol."""

    def __init__(self, server_cmd: list[str]) -> None:
        self.server_cmd = server_cmd
        self.transport: AsyncStdioTransport | None = None
        self._response_futures: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._reader_task: asyncio.Task[None] | None = None
        self._id = 0
        self.proc: asyncio.subprocess.Process | None = None
        self._notification_handlers: dict[str, Any] = {}
        self._analysis_complete_event = asyncio.Event()

    async def _send_result(self, id_: int, result: Any = None) -> None:
        """Send a result response (not typically used by clients)."""
        if self.transport is None:
            return
        await self.transport.send({"jsonrpc": "2.0", "id": id_, "result": result})

    async def connect(self) -> None:
        """Connect to the LSP server."""
        self.proc = await asyncio.create_subprocess_exec(
            *self.server_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if self.proc.returncode is not None:
            raise RuntimeError("Failed to start LSP server")
        self.transport = AsyncStdioTransport(self.proc)
        self._reader_task = asyncio.create_task(self._reader())

    async def _reader(self) -> None:
        """Reads messages from the server and dispatches them."""
        while self.transport:
            message = await self.transport.read_message()
            if message is None:
                break
            if "id" in message:
                msg_id = message["id"]
                fut = self._response_futures.get(msg_id)
                if fut and not fut.done():
                    fut.set_result(message)
            elif "method" in message:
                # Handle notifications
                method = message["method"]
                await self._handle_notification(method, message.get("params", {}))

        # If the reader exits, notify all pending futures
        for future in self._response_futures.values():
            if not future.done():
                future.set_exception(RuntimeError("LSP connection lost"))

    def _next_id(self) -> int:
        """Get the next request ID."""
        self._id += 1
        return self._id

    async def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a request and wait for response."""
        if self.transport is None:
            raise RuntimeError("Not connected")

        msg_id = self._next_id()
        future = asyncio.get_event_loop().create_future()
        self._response_futures[msg_id] = future

        await self.transport.send(
            {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}}
        )

        try:
            async with asyncio.timeout(60.0):
                response = await future
            if "error" in response:
                raise RuntimeError(f"LSP error for {method}: {response['error']}")
            return response.get("result", {})
        except TimeoutError:
            raise TimeoutError(f"Timed out waiting for {method}")
        finally:
            if msg_id in self._response_futures:
                del self._response_futures[msg_id]

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a notification (no response expected)."""
        if self.transport is None:
            raise RuntimeError("Not connected")
        await self.transport.send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    async def _handle_notification(self, method: str, params: dict[str, Any]) -> None:
        """Handle incoming notifications from the server."""
        if method == "textDocument/publishDiagnostics":
            return
        logger.debug(f"Received notification: {method} with params: {params}")

        if method == "pyright/endProgress":
            # basedpyright/pyright sends this when analysis is complete
            self._analysis_complete_event.set()
            logger.info("Analysis complete")
        elif method == "pyright/beginProgress":
            logger.debug("Analysis started")
        elif method == "pyright/reportProgress":
            logger.debug(f"Analysis progress: {params}")
        elif method == "textDocument/publishDiagnostics":
            # Diagnostics published - analysis is progressing/complete for this file
            uri = params.get("uri", "unknown file")
            diagnostics = params.get("diagnostics", [])
            logger.debug(f"Diagnostics published for {uri}: {len(diagnostics)} items")

        # Call custom handlers if registered
        handler = self._notification_handlers.get(method)
        if handler:
            await handler(params)

    def register_notification_handler(self, method: str, handler: Any) -> None:
        """Register a custom notification handler."""
        self._notification_handlers[method] = handler

    async def wait_for_analysis_complete(self) -> None:
        """Wait for analysis to complete."""
        try:
            async with asyncio.timeout(60):
                await self._analysis_complete_event.wait()
        except TimeoutError:
            logger.warning("Timeout waiting for analysis to complete")
        finally:
            self._analysis_complete_event.clear()

    async def initialize(self, root_uri: str) -> dict[str, Any]:
        """Initialize the LSP server."""
        params = {
            "processId": os.getpid(),
            "clientInfo": {"name": "unused-func-detector", "version": "0.1.0"},
            "rootUri": root_uri,
            "workspaceFolders": [{"uri": root_uri, "name": "workspace"}],
            "capabilities": {
                "textDocument": {
                    "references": {"dynamicRegistration": True},
                    "hover": {"dynamicRegistration": True},
                },
                "workspace": {"workspaceFolders": True},
            },
        }
        result = await self.request("initialize", params=params)
        await self.notify("initialized", params={})
        return result

    async def references(
        self,
        text_document_uri: str,
        line0: int,
        char0: int,
        include_declaration: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Query the LSP server for references at a given zero-based position.

        Args:
            text_document_uri: File URI (e.g., "file:///.../foo.py").
            line0: 0-based line index.
            char0: 0-based character index.
            include_declaration: Whether to include the declaration site as a "reference".

        Returns:
            A list of Location (or Location-like) dicts: [{"uri": str, "range": {...}}, ...]
        """
        params = {
            "textDocument": {"uri": text_document_uri},
            "position": {"line": line0, "character": char0},
            "context": {"includeDeclaration": include_declaration},
        }

        result = await self.request("textDocument/references", params=params)

        if result is None:
            return []
        return result if isinstance(result, list) else []

    async def hover(
        self,
        text_document_uri: str,
        line0: int,
        char0: int,
    ) -> dict[str, Any] | None:
        """
        Query the LSP server for hover information at a given zero-based position.

        Args:
            text_document_uri: File URI (e.g., "file:///.../foo.py").
            line0: 0-based line index.
            char0: 0-based character index.

        Returns:
            Hover response dict or None if no hover information available.
        """
        params = {
            "textDocument": {"uri": text_document_uri},
            "position": {"line": line0, "character": char0},
        }

        result = await self.request("textDocument/hover", params=params)
        return result if result else None

    async def shutdown(self) -> None:
        """Shutdown the LSP connection."""
        if self._reader_task is not None:
            self._reader_task.cancel()
        try:
            await self.notify("shutdown")
        except Exception:
            logger.debug("Failed to shutdown LSP server gracefully")
        try:
            await self.notify("exit")
        except Exception:
            pass
        if self.transport:
            await self.transport.close()
