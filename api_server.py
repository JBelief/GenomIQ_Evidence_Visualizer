from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from genomiq.agents import GenomIQMultiAgentOrchestrator  # noqa: E402
from genomiq.approval import require_human_approval  # noqa: E402
from genomiq.evidence import build_evidence_retriever  # noqa: E402
from genomiq.visualizer import write_visual_report  # noqa: E402
from genomiq.work_context import build_workplace_retriever  # noqa: E402


ARTIFACT_DIR = ROOT / "artifacts"


def build_openapi(base_url: str) -> dict[str, Any]:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "GenomIQ Evidence Visualizer API",
            "version": "0.1.0",
            "description": "Cost-safe API wrapper for generating GenomIQ interactive research reports.",
        },
        "servers": [{"url": base_url.rstrip("/")}],
        "paths": {
            "/health": {
                "get": {
                    "operationId": "health_check",
                    "summary": "Check service health",
                    "responses": {"200": {"description": "Service is healthy"}},
                }
            },
            "/generate-report": {
                "post": {
                    "operationId": "generate_genomiq_report",
                    "summary": "Generate a GenomIQ interactive report from genomic variant text or VCF-like input",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "case_text": {
                                            "type": "string",
                                            "description": "Synthetic or de-identified free text, coordinate snippet, or VCF-like variant input.",
                                        },
                                        "use_ncbi_live": {
                                            "type": "boolean",
                                            "default": False,
                                            "description": "Enable live NCBI dbSNP lookup for coordinate markers.",
                                        },
                                        "use_pubmed_live": {
                                            "type": "boolean",
                                            "default": False,
                                            "description": "Enable live PubMed E-utilities evidence lookup.",
                                        },
                                        "approved_for_export": {
                                            "type": "boolean",
                                            "default": False,
                                            "description": "Human approval flag. Must be true before report export.",
                                        },
                                    },
                                    "required": ["case_text"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Report generation result",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "claim_status": {"type": "string"},
                                            "parsed_variants": {"type": "array", "items": {"type": "string"}},
                                            "dbsnp_ids": {"type": "array", "items": {"type": "string"}},
                                            "pubmed_ids": {"type": "array", "items": {"type": "string"}},
                                            "verification_findings": {"type": "array", "items": {"type": "object"}},
                                            "report_url": {"type": "string"},
                                            "report_json_url": {"type": "string"},
                                            "safety_note": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
    }


def generate_report(payload: dict[str, Any], base_url: str) -> tuple[int, dict[str, Any]]:
    case_text = str(payload.get("case_text", "")).strip()
    if not case_text:
        return HTTPStatus.BAD_REQUEST, {"status": "error", "message": "case_text is required."}

    previous_ncbi = os.environ.get("GENOMIQ_USE_NCBI_LIVE")
    previous_pubmed = os.environ.get("GENOMIQ_USE_PUBMED_LIVE")
    try:
        os.environ["GENOMIQ_USE_NCBI_LIVE"] = "true" if payload.get("use_ncbi_live") else "false"
        os.environ["GENOMIQ_USE_PUBMED_LIVE"] = "true" if payload.get("use_pubmed_live") else "false"

        orchestrator = GenomIQMultiAgentOrchestrator(
            evidence_retriever=build_evidence_retriever(),
            workplace_retriever=build_workplace_retriever(),
        )
        parsed_case, evidence, _workplace_context, assessment = orchestrator.run(case_text)
    finally:
        _restore_env("GENOMIQ_USE_NCBI_LIVE", previous_ncbi)
        _restore_env("GENOMIQ_USE_PUBMED_LIVE", previous_pubmed)

    approved_for_export = bool(payload.get("approved_for_export"))
    export_allowed = require_human_approval(assessment, auto_approve=approved_for_export)

    dbsnp_ids = [
        item.dbsnp_id
        for item in assessment.variant_annotations
        if item.dbsnp_id.startswith("rs")
    ]
    pubmed_ids = [item.doc_id for item in evidence if item.doc_id.startswith("PMID:")]

    response: dict[str, Any] = {
        "status": "report_generated" if export_allowed else "approval_required",
        "claim_status": assessment.claim_status.value,
        "tier": assessment.tier.value,
        "organ": assessment.organ,
        "confidence": assessment.confidence,
        "parsed_variants": parsed_case.variants,
        "dbsnp_ids": dbsnp_ids,
        "pubmed_ids": pubmed_ids,
        "variant_annotations": [asdict(item) for item in assessment.variant_annotations],
        "evidence_sources": [asdict(item) for item in assessment.evidence_sources],
        "verification_findings": [asdict(item) for item in assessment.verification_findings],
        "safety_note": "Research prototype only; not for diagnosis or treatment.",
    }

    if export_allowed:
        report = write_visual_report(assessment, ARTIFACT_DIR)
        html_name = quote(Path(report.html_path).name)
        json_name = quote(Path(report.json_path).name)
        cache_version = str(int(Path(report.html_path).stat().st_mtime))
        response["report_url"] = f"{base_url.rstrip('/')}/reports/{html_name}?v={cache_version}"
        response["report_json_url"] = f"{base_url.rstrip('/')}/reports/{json_name}?v={cache_version}"
    else:
        response["message"] = "Human approval is required before exporting the interactive report."

    return HTTPStatus.OK, response


def _restore_env(name: str, previous_value: str | None) -> None:
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


class GenomIQRequestHandler(BaseHTTPRequestHandler):
    server_version = "GenomIQAPI/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/openapi.json":
            self._send_json(build_openapi(self._base_url()))
            return
        if parsed.path.startswith("/reports/"):
            self._send_report_file(parsed.path.removeprefix("/reports/"))
            return
        self._send_json({"status": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/generate-report":
            self._send_json({"status": "not_found"}, HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"status": "error", "message": "Invalid JSON body."}, HTTPStatus.BAD_REQUEST)
            return

        status, response = generate_report(payload, self._base_url())
        self._send_json(response, status)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("genomiq-api: " + format % args + "\n")

    def _base_url(self) -> str:
        host = self.headers.get("Host", f"localhost:{self.server.server_port}")
        scheme = self.headers.get("X-Forwarded-Proto", "http")
        return f"{scheme}://{host}"

    def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_report_file(self, filename: str) -> None:
        safe_name = Path(filename).name
        file_path = ARTIFACT_DIR / safe_name
        if not file_path.exists() or not file_path.is_file():
            self._send_json({"status": "not_found"}, HTTPStatus.NOT_FOUND)
            return

        content_type = "text/html; charset=utf-8" if file_path.suffix == ".html" else "application/json; charset=utf-8"
        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)


def main() -> int:
    port = int(os.environ.get("GENOMIQ_API_PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), GenomIQRequestHandler)
    print(f"GenomIQ API server running at http://localhost:{port}")
    print(f"OpenAPI spec: http://localhost:{port}/openapi.json")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping GenomIQ API server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
