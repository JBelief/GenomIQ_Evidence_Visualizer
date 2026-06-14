from __future__ import annotations

import argparse
import os
from pathlib import Path

from genomiq.agents import GenomIQMultiAgentOrchestrator
from genomiq.approval import require_human_approval
from genomiq.evidence import build_evidence_retriever
from genomiq.visualizer import write_visual_report
from genomiq.work_context import build_workplace_retriever


def run_pipeline(
    case_text: str,
    output_dir: Path,
    auto_approve: bool = False,
    use_ncbi_live: bool = False,
    use_pubmed_live: bool = False,
) -> int:
    if use_ncbi_live:
        os.environ["GENOMIQ_USE_NCBI_LIVE"] = "true"
    if use_pubmed_live:
        os.environ["GENOMIQ_USE_PUBMED_LIVE"] = "true"

    print("Running GenomIQ multi-agent reasoning workflow...")
    if use_ncbi_live or use_pubmed_live:
        print(
            "NCBI source interpretation enabled: "
            f"dbSNP={os.environ.get('GENOMIQ_USE_NCBI_LIVE', 'false')}, "
            f"PubMed={os.environ.get('GENOMIQ_USE_PUBMED_LIVE', 'false')}"
        )
    orchestrator = GenomIQMultiAgentOrchestrator(
        evidence_retriever=build_evidence_retriever(),
        workplace_retriever=build_workplace_retriever(),
    )
    parsed_case, evidence, workplace_context, assessment = orchestrator.run(case_text)

    print(f"Markers: {', '.join(parsed_case.variants)}")
    print(f"Research area: {parsed_case.primary_research_area}")

    print("\nAgent reasoning trace:")
    for step in assessment.agent_trace:
        print(f"- {step.agent_name}: {step.output_summary}")

    print("\nRetrieved literature evidence:")
    for item in evidence:
        print(f"- {item.doc_id}: {item.title} (confidence={item.confidence})")

    print("\nVariant annotations:")
    for item in assessment.variant_annotations:
        print(
            f"- {item.variant}: {item.coordinate} {item.reference}>{item.alternate}, "
            f"gene={item.gene_name}, dbSNP={item.dbsnp_id}, note={item.consequence}"
        )

    print("\nRetrieved work-context signals:")
    for item in workplace_context:
        print(f"- {item.context_id}: {item.source_label}")

    print("\nTop disease vulnerability hypotheses:")
    for index, disease in enumerate(assessment.top_diseases, start=1):
        print(f"{index}. {disease.disease} score={disease.score} genes={', '.join(disease.risk_genes) or 'metadata'}")

    print("\nVerification findings:")
    for finding in assessment.verification_findings:
        print(f"- {finding.level.upper()} {finding.check_name}: {finding.detail}")

    print(f"Assessment: {assessment.tier.value} / {assessment.claim_status.value}")

    if not require_human_approval(assessment, auto_approve=auto_approve):
        print("Report export was not approved.")
        return 2

    report = write_visual_report(assessment, output_dir)
    print("\nReport exported.")
    print(f"HTML: {report.html_path}")
    print(f"JSON: {report.json_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the GenomIQ Evidence Visualizer demo pipeline.")
    parser.add_argument("--case", type=Path, required=True, help="Path to a synthetic research case text file.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"), help="Directory for generated reports.")
    parser.add_argument("--auto-approve", action="store_true", help="Skip interactive approval for automated tests.")
    parser.add_argument("--use-ncbi-live", action="store_true", help="Enable live NCBI dbSNP lookup for coordinate markers.")
    parser.add_argument("--use-pubmed-live", action="store_true", help="Enable live PubMed E-utilities evidence lookup.")
    args = parser.parse_args()

    case_text = args.case.read_text(encoding="utf-8")
    return run_pipeline(
        case_text,
        args.output_dir,
        auto_approve=args.auto_approve,
        use_ncbi_live=args.use_ncbi_live,
        use_pubmed_live=args.use_pubmed_live,
    )


if __name__ == "__main__":
    raise SystemExit(main())
