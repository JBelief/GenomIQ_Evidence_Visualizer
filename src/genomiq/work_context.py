from __future__ import annotations

import os
from typing import Protocol

from genomiq.schema import ParsedCase, WorkplaceContext


class WorkplaceContextRetriever(Protocol):
    def retrieve(self, parsed_case: ParsedCase) -> list[WorkplaceContext]:
        """Return permission-scoped workplace context records."""


class DemoWorkIQContextRetriever:
    """Work IQ-style adapter using synthetic, approved workplace context."""

    def retrieve(self, parsed_case: ParsedCase) -> list[WorkplaceContext]:
        marker_text = ", ".join(parsed_case.variants)
        return [
            WorkplaceContext(
                context_id="WORKIQ-DEMO-MTG-001",
                source_label="Synthetic tumor board meeting note",
                summary=(
                    "Demo research team previously agreed that BRCA/PARP examples must be "
                    "labeled research-only and require citation coverage before export."
                ),
                approved_for_demo=True,
            ),
            WorkplaceContext(
                context_id="WORKIQ-DEMO-POLICY-002",
                source_label="Synthetic lab safety policy",
                summary=f"Demo policy allows non-identifiable marker summaries only. Current markers: {marker_text}.",
                approved_for_demo=True,
            ),
        ]


def build_workplace_retriever() -> WorkplaceContextRetriever:
    use_real_workiq = os.environ.get("GENOMIQ_USE_REAL_WORKIQ", "false").lower() == "true"
    if use_real_workiq:
        raise NotImplementedError(
            "Real Work IQ integration must be configured with tenant approval and the Work IQ MCP server."
        )
    return DemoWorkIQContextRetriever()
