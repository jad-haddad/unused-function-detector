"""LSP Transport via Async Stdio."""

import asyncio
import json
import logging
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
