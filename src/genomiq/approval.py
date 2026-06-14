from __future__ import annotations

from genomiq.schema import ClaimStatus, RiskAssessment


def require_human_approval(assessment: RiskAssessment, auto_approve: bool = False) -> bool:
    if assessment.claim_status == ClaimStatus.BLOCKED:
        print("Export blocked by safety gate.")
        for reason in assessment.blocked_reasons:
            print(f"- {reason}")
        return False

    print("\nHuman approval required before exporting the research visual report.")
    print(f"Tier: {assessment.tier.value}")
    print(f"Confidence: {assessment.confidence}")
    print(f"Evidence IDs: {', '.join(assessment.evidence_ids) or 'none'}")
    print("Safety note: research prototype only; not for diagnosis or treatment.")

    if auto_approve:
        return True

    answer = input("Approve export? (yes/no): ").strip().lower()
    return answer in {"yes", "y"}

