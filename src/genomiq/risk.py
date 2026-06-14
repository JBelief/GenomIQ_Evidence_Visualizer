from __future__ import annotations

from statistics import mean

from genomiq.schema import (
    ClaimStatus,
    EvidenceSource,
    ParsedCase,
    RiskAssessment,
    RiskTier,
    WorkplaceContext,
)


def assess_research_risk(
    parsed_case: ParsedCase,
    evidence: list[EvidenceSource],
    workplace_context: list[WorkplaceContext],
    min_confidence: float = 0.70,
) -> RiskAssessment:
    blocked_reasons: list[str] = []

    if parsed_case.contains_sensitive_identifiers:
        blocked_reasons.append("Input may contain sensitive identifiers; export is blocked.")

    supported_evidence = [item for item in evidence if item.confidence >= min_confidence]
    if not supported_evidence:
        blocked_reasons.append("No evidence source met the minimum confidence threshold.")

    if not all(ctx.approved_for_demo for ctx in workplace_context):
        blocked_reasons.append("One or more workplace context records are not approved for demo export.")

    markers = set(parsed_case.variants)
    has_brca_parp_signal = {"BRCA1_mut", "PARP_pathway_dependency"} <= markers
    confidence = mean([parsed_case.confidence_score, *[item.confidence for item in supported_evidence]]) if supported_evidence else parsed_case.confidence_score

    if blocked_reasons:
        tier = RiskTier.LOW
        status = ClaimStatus.BLOCKED
        rationale = "Visualization is blocked because the safety gate did not pass."
    elif has_brca_parp_signal and confidence >= 0.80:
        tier = RiskTier.HIGH
        status = ClaimStatus.SUPPORTED
        rationale = (
            "Research-only high-priority signal: BRCA pathway disruption with PARP pathway dependency "
            "has grounded demo evidence. This is not a treatment recommendation."
        )
    elif confidence >= min_confidence:
        tier = RiskTier.MEDIUM
        status = ClaimStatus.SUPPORTED
        rationale = "Research-only moderate evidence signal with citation coverage."
    else:
        tier = RiskTier.LOW
        status = ClaimStatus.INSUFFICIENT_EVIDENCE
        rationale = "Insufficient grounded evidence for a research visualization claim."

    organ = "Ovary" if "ovarian" in parsed_case.primary_research_area.lower() else "General"

    return RiskAssessment(
        tier=tier,
        organ=organ,
        confidence=round(confidence, 3),
        claim_status=status,
        rationale=rationale,
        evidence_ids=[item.doc_id for item in supported_evidence],
        workplace_context_ids=[ctx.context_id for ctx in workplace_context],
        blocked_reasons=blocked_reasons,
    )

