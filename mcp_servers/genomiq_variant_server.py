from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from genomiq.mcp_tools import VariantAnnotationMCPTool  # noqa: E402


SERVER_INFO = {
    "name": "genomiq-variant-mcp",
    "version": "0.1.0",
}

ANNOTATE_VARIANT_TOOL = {
    "name": "annotate_variant",
    "description": (
        "Annotate a genomic variant marker or coordinate. Accepts demo markers such as BRCA1_mut "
        "and coordinate markers such as chr7:182734 or chr7:182734:A>G. Optionally uses NCBI "
        "dbSNP when GENOMIQ_USE_NCBI_LIVE=true."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "variant": {
                "type": "string",
                "description": "Variant marker, coordinate, or VCF-derived marker.",
            }
        },
        "required": ["variant"],
    },
}


def handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": [ANNOTATE_VARIANT_TOOL]},
        }

    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        if name != "annotate_variant":
            return _error(request_id, -32602, f"Unknown tool: {name}")
        variant = arguments.get("variant")
        if not isinstance(variant, str) or not variant.strip():
            return _error(request_id, -32602, "annotate_variant requires a non-empty string argument: variant")

        annotation = VariantAnnotationMCPTool().annotate(variant.strip())
        payload = asdict(annotation)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload, ensure_ascii=True, indent=2),
                    }
                ],
                "structuredContent": payload,
                "isError": False,
            },
        }

    if request_id is None:
        return None

    return _error(request_id, -32601, f"Method not found: {method}")


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if line == b"":
            return None
        if line in {b"\r\n", b"\n"}:
            break
        key, _, value = line.decode("ascii").partition(":")
        headers[key.lower()] = value.strip()

    content_length = int(headers.get("content-length", "0"))
    if content_length <= 0:
        return None
    body = sys.stdin.buffer.read(content_length)
    return json.loads(body.decode("utf-8"))


def write_message(message: dict[str, Any]) -> None:
    encoded = json.dumps(message, ensure_ascii=True).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def serve() -> int:
    while True:
        request = read_message()
        if request is None:
            return 0
        response = handle_request(request)
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    raise SystemExit(serve())
