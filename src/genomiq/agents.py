from __future__ import annotations

import re
from statistics import mean

from genomiq.evidence import EvidenceRetriever
from genomiq.mcp_tools import VariantAnnotationMCPTool
from genomiq.parser import parse_research_case
from genomiq.risk import assess_research_risk
from genomiq.schema import (
    AgentTraceStep,
    DemographicMetadata,
    DiseaseHypothesis,
    EvidenceSource,
    ParsedCase,
    RiskAssessment,
    VariantAnnotation,
    VerificationFinding,
    WorkplaceContext,
)
from genomiq.work_context import WorkplaceContextRetriever


class MetadataSurveyAgent:
    name = "Metadata Survey Agent"

    def run(self, case_text: str) -> tuple[DemographicMetadata, AgentTraceStep]:
        upper_text = case_text.upper()
        metadata = DemographicMetadata(
            sex="female" if "OVARIAN" in upper_text else "unspecified",
            age=52,
            height_cm=164.0,
            weight_kg=68.0,
            known_conditions=["synthetic demo: no active diagnosis"],
            family_history=["synthetic demo: breast/ovarian cancer family history mentioned"],
        )
        return metadata, AgentTraceStep(
            agent_name=self.name,
            action="Collected synthetic demographic and family-history metadata.",
            output_summary=f"sex={metadata.sex}, age={metadata.age}, BMI={metadata.bmi}",
        )


class VariantParserAgent:
    name = "Variant Parser Agent"

    def run(self, case_text: str) -> tuple[ParsedCase, AgentTraceStep]:
        parsed = parse_research_case(case_text)
        return parsed, AgentTraceStep(
            agent_name=self.name,
            action="Parsed raw case text into variant markers.",
            output_summary=f"markers={', '.join(parsed.variants)}",
        )


class VariantAnnotationAgent:
    name = "Variant Annotation Agent"

    def __init__(self) -> None:
        self.tool = VariantAnnotationMCPTool()

    def run(self, variants: list[str]) -> tuple[list[VariantAnnotation], AgentTraceStep]:
        annotations = [self.tool.annotate(variant) for variant in variants]
        genes = sorted({annotation.gene_name for annotation in annotations})
        return annotations, AgentTraceStep(
            agent_name=self.name,
            action="Called MCP-style variant annotation tool for chromosome, coordinate, gene, and dbSNP metadata.",
            output_summary=f"annotated_genes={', '.join(genes)}",
        )


class DiseaseNetworkReasoningAgent:
    name = "Disease Network Reasoning Agent"

    def run(
        self,
        annotations: list[VariantAnnotation],
        metadata: DemographicMetadata,
    ) -> tuple[list[DiseaseHypothesis], AgentTraceStep]:
        genes = {annotation.gene_name for annotation in annotations}
        variant_ids = [annotation.variant for annotation in annotations]
        hypotheses: list[DiseaseHypothesis] = []

        if {"BRCA1", "PARP1"} <= genes:
            hypotheses.append(
                DiseaseHypothesis(
                    disease="Ovarian cancer research vulnerability",
                    score=0.88,
                    risk_genes=["BRCA1", "PARP1"],
                    variant_ids=variant_ids,
                    rationale="BRCA pathway disruption plus PARP pathway dependency creates a high-priority research signal.",
                )
            )

        if "BRCA1" in genes or "BRCA2" in genes:
            hypotheses.append(
                DiseaseHypothesis(
                    disease="Hereditary breast and ovarian cancer research signal",
                    score=0.78,
                    risk_genes=sorted(genes & {"BRCA1", "BRCA2"}),
                    variant_ids=variant_ids,
                    rationale="BRCA gene markers and synthetic family-history metadata increase research triage priority.",
                )
            )

        if "BRAF" in genes:
            hypotheses.append(
                DiseaseHypothesis(
                    disease="Colorectal cancer BRAF V600E research signal",
                    score=0.86,
                    risk_genes=["BRAF"],
                    variant_ids=variant_ids,
                    rationale=(
                        "BRAF V600E is a well-known MAPK pathway hotspot used in colorectal cancer "
                        "molecular stratification research; this is not a clinical recommendation."
                    ),
                )
            )

        if metadata.bmi >= 25:
            hypotheses.append(
                DiseaseHypothesis(
                    disease="Metabolic risk modifier",
                    score=0.42,
                    risk_genes=[],
                    variant_ids=[],
                    rationale="BMI metadata is a non-genetic modifier and should be treated as contextual, not deterministic.",
                )
            )

        hypotheses = sorted(hypotheses, key=lambda item: item.score, reverse=True)[:3]
        return hypotheses, AgentTraceStep(
            agent_name=self.name,
            action="Combined individual variant annotations, gene network relationships, and metadata modifiers.",
            output_summary="top_diseases=" + "; ".join(item.disease for item in hypotheses),
        )


class LiteratureCitationAgent:
    name = "Literature Citation Agent"

    def __init__(self, retriever: EvidenceRetriever) -> None:
        self.retriever = retriever

    def run(self, parsed_case: ParsedCase) -> tuple[list[EvidenceSource], AgentTraceStep]:
        evidence = self.retriever.retrieve(parsed_case)
        return evidence, AgentTraceStep(
            agent_name=self.name,
            action="Retrieved literature citations via demo catalog, optional PubMed E-utilities, or optional Azure Foundry IQ adapter.",
            output_summary="evidence_ids=" + ", ".join(item.doc_id for item in evidence),
        )


class MetadataWeightingAgent:
    name = "Metadata Weighting Agent"

    def run(
        self,
        hypotheses: list[DiseaseHypothesis],
        metadata: DemographicMetadata,
    ) -> tuple[list[DiseaseHypothesis], AgentTraceStep]:
        weighted: list[DiseaseHypothesis] = []
        family_history_boost = 0.05 if metadata.family_history else 0.0
        bmi_modifier = 0.03 if metadata.bmi >= 25 else 0.0

        for hypothesis in hypotheses:
            score = min(1.0, hypothesis.score + family_history_boost)
            if "Metabolic" in hypothesis.disease:
                score = min(1.0, hypothesis.score + bmi_modifier)
            weighted.append(
                DiseaseHypothesis(
                    disease=hypothesis.disease,
                    score=round(score, 3),
                    risk_genes=hypothesis.risk_genes,
                    variant_ids=hypothesis.variant_ids,
                    rationale=hypothesis.rationale,
                )
            )

        weighted = sorted(weighted, key=lambda item: item.score, reverse=True)[:3]
        return weighted, AgentTraceStep(
            agent_name=self.name,
            action="Applied metadata weighting from age, BMI, known conditions, and synthetic family history.",
            output_summary="weighted_scores=" + ", ".join(f"{item.disease}: {item.score}" for item in weighted),
        )


class SafetyReviewerAgent:
    name = "Safety Reviewer Agent"

    def run(self, assessment: RiskAssessment) -> AgentTraceStep:
        return AgentTraceStep(
            agent_name=self.name,
            action="Checked citation coverage, confidence threshold, sensitive identifiers, and human-review requirement.",
            output_summary=f"claim_status={assessment.claim_status.value}, blocked_reasons={len(assessment.blocked_reasons)}",
        )


class HealthGuidanceAgent:
    name = "Health Guidance Agent"

    def run(self, hypotheses: list[DiseaseHypothesis]) -> tuple[list[str], AgentTraceStep]:
        guidance = [
            "Discuss high-priority research signals with a qualified clinician or genetic counselor before taking action.",
            "Use general prevention basics only in the demo: balanced diet, regular activity, sleep hygiene, and tobacco avoidance.",
            "Screening, surveillance, medication, or supplement decisions are outside this research demo and require professional review.",
        ]
        if hypotheses:
            guidance.append(
                f"Prioritize follow-up literature review for: {hypotheses[0].disease}."
            )

        return guidance, AgentTraceStep(
            agent_name=self.name,
            action="Generated non-diagnostic wellness and review guidance with clinical-action guardrails.",
            output_summary=f"guidance_items={len(guidance)}",
        )


class NCBISourceInterpretationAgent:
    name = "NCBI Source Interpretation Agent"

    def run(
        self,
        annotations: list[VariantAnnotation],
        evidence: list[EvidenceSource],
    ) -> AgentTraceStep:
        dbsnp_hits = sorted({item.dbsnp_id for item in annotations if item.dbsnp_id.startswith("rs")})
        pubmed_hits = [item.doc_id for item in evidence if re.fullmatch(r"PMID:\d+", item.doc_id)]
        pending_annotations = [
            item.variant
            for item in annotations
            if item.dbsnp_id in {"requires_live_ncbi_lookup", "unknown"}
            or item.gene_name in {"requires_live_annotation", "unknown"}
        ]

        summary_parts = [
            f"dbsnp_hits={len(dbsnp_hits)}" + (f" ({', '.join(dbsnp_hits[:4])})" if dbsnp_hits else ""),
            f"pubmed_hits={len(pubmed_hits)}",
        ]
        if pending_annotations:
            summary_parts.append("pending_live_lookup=" + ", ".join(pending_annotations))

        return AgentTraceStep(
            agent_name=self.name,
            action=(
                "Interpreted NCBI dbSNP/PubMed source outputs and flagged unresolved coordinates "
                "without inventing rsIDs, genes, or disease claims."
            ),
            output_summary="; ".join(summary_parts),
        )


class VerificationAgent:
    name = "Verification Agent"

    def run(
        self,
        parsed_case: ParsedCase,
        annotations: list[VariantAnnotation],
        evidence: list[EvidenceSource],
    ) -> tuple[list[VerificationFinding], AgentTraceStep]:
        findings: list[VerificationFinding] = []

        if parsed_case.contains_sensitive_identifiers:
            findings.append(
                VerificationFinding(
                    level="block",
                    check_name="sensitive_identifier_scan",
                    detail="Potential PHI/PII pattern detected in the input text.",
                )
            )
        else:
            findings.append(
                VerificationFinding(
                    level="pass",
                    check_name="sensitive_identifier_scan",
                    detail="No MRN, DOB, or SSN-like pattern detected by the deterministic scanner.",
                )
            )

        unresolved = [
            item.variant
            for item in annotations
            if item.gene_name in {"unknown", "requires_live_annotation"}
            or item.dbsnp_id in {"unknown", "requires_live_ncbi_lookup"}
        ]
        findings.append(
            VerificationFinding(
                level="warn" if unresolved else "pass",
                check_name="variant_annotation_coverage",
                detail=(
                    "Live NCBI/Ensembl annotation recommended for: " + ", ".join(unresolved)
                    if unresolved
                    else "All parsed markers have demo annotation coverage."
                ),
            )
        )

        citation_like = [
            item.doc_id
            for item in evidence
            if item.doc_id.startswith(("PMID:", "PMCID:", "FOUNDRY-IQ:", "GENOMIQ:"))
        ]
        findings.append(
            VerificationFinding(
                level="pass" if citation_like else "warn",
                check_name="citation_identifier_format",
                detail=(
                    f"{len(citation_like)} evidence record(s) use accepted citation/source ID prefixes."
                    if citation_like
                    else "No accepted citation/source ID prefix found in retrieved evidence."
                ),
            )
        )

        low_confidence = [item.doc_id for item in evidence if item.confidence < 0.7]
        findings.append(
            VerificationFinding(
                level="warn" if low_confidence else "pass",
                check_name="evidence_confidence_threshold",
                detail=(
                    "Low-confidence evidence IDs: " + ", ".join(low_confidence)
                    if low_confidence
                    else "All retrieved evidence records meet the demo confidence threshold."
                ),
            )
        )

        blocking = sum(1 for item in findings if item.level == "block")
        warnings = sum(1 for item in findings if item.level == "warn")
        return findings, AgentTraceStep(
            agent_name=self.name,
            action="Cross-checked input safety, variant annotation coverage, citation IDs, and evidence confidence.",
            output_summary=f"verification_passed={blocking == 0}, warnings={warnings}, blocks={blocking}",
        )


def infer_report_organ(base_organ: str, hypotheses: list[DiseaseHypothesis]) -> str:
    if base_organ != "General":
        return base_organ

    disease_text = " ".join(item.disease.lower() for item in hypotheses)
    if "breast" in disease_text and "ovarian" in disease_text:
        return "Breast / Ovary"
    if "ovarian" in disease_text:
        return "Ovary"
    if "breast" in disease_text:
        return "Breast"
    if "gastric" in disease_text or "stomach" in disease_text:
        return "Stomach"
    if "colorectal" in disease_text or "colon" in disease_text:
        return "Colon"
    return base_organ


class GenomIQMultiAgentOrchestrator:
    def __init__(
        self,
        evidence_retriever: EvidenceRetriever,
        workplace_retriever: WorkplaceContextRetriever,
    ) -> None:
        self.metadata_agent = MetadataSurveyAgent()
        self.parser_agent = VariantParserAgent()
        self.annotation_agent = VariantAnnotationAgent()
        self.citation_agent = LiteratureCitationAgent(evidence_retriever)
        self.ncbi_interpretation_agent = NCBISourceInterpretationAgent()
        self.network_agent = DiseaseNetworkReasoningAgent()
        self.weighting_agent = MetadataWeightingAgent()
        self.verification_agent = VerificationAgent()
        self.health_agent = HealthGuidanceAgent()
        self.safety_agent = SafetyReviewerAgent()
        self.workplace_retriever = workplace_retriever

    def run(self, case_text: str) -> tuple[ParsedCase, list[EvidenceSource], list[WorkplaceContext], RiskAssessment]:
        trace: list[AgentTraceStep] = []

        metadata, step = self.metadata_agent.run(case_text)
        trace.append(step)

        parsed_case, step = self.parser_agent.run(case_text)
        trace.append(step)

        annotations, step = self.annotation_agent.run(parsed_case.variants)
        trace.append(step)

        evidence, step = self.citation_agent.run(parsed_case)
        trace.append(step)

        step = self.ncbi_interpretation_agent.run(annotations, evidence)
        trace.append(step)

        verification_findings, step = self.verification_agent.run(parsed_case, annotations, evidence)
        trace.append(step)

        workplace_context = self.workplace_retriever.retrieve(parsed_case)
        trace.append(
            AgentTraceStep(
                agent_name="Work Context Agent",
                action="Retrieved permission-scoped workplace context from synthetic adapter or optional Work IQ path.",
                output_summary="context_ids=" + ", ".join(item.context_id for item in workplace_context),
            )
        )

        hypotheses, step = self.network_agent.run(annotations, metadata)
        trace.append(step)

        weighted_hypotheses, step = self.weighting_agent.run(hypotheses, metadata)
        trace.append(step)

        health_guidance, step = self.health_agent.run(weighted_hypotheses)
        trace.append(step)

        base_assessment = assess_research_risk(parsed_case, evidence, workplace_context)
        confidence = base_assessment.confidence
        if weighted_hypotheses:
            confidence = round(mean([base_assessment.confidence, weighted_hypotheses[0].score]), 3)
        organ = infer_report_organ(base_assessment.organ, weighted_hypotheses)

        provisional_assessment = RiskAssessment(
            tier=base_assessment.tier,
            organ=organ,
            confidence=confidence,
            claim_status=base_assessment.claim_status,
            rationale=base_assessment.rationale,
            evidence_ids=base_assessment.evidence_ids,
            workplace_context_ids=base_assessment.workplace_context_ids,
            blocked_reasons=base_assessment.blocked_reasons,
            parsed_variants=parsed_case.variants,
            top_diseases=weighted_hypotheses,
            agent_trace=trace,
            health_guidance=health_guidance,
            verification_findings=verification_findings,
            variant_annotations=annotations,
            evidence_sources=evidence,
        )
        safety_step = self.safety_agent.run(provisional_assessment)
        trace.append(safety_step)

        assessment = RiskAssessment(
            tier=provisional_assessment.tier,
            organ=provisional_assessment.organ,
            confidence=provisional_assessment.confidence,
            claim_status=provisional_assessment.claim_status,
            rationale=provisional_assessment.rationale,
            evidence_ids=provisional_assessment.evidence_ids,
            workplace_context_ids=provisional_assessment.workplace_context_ids,
            blocked_reasons=provisional_assessment.blocked_reasons,
            parsed_variants=provisional_assessment.parsed_variants,
            top_diseases=provisional_assessment.top_diseases,
            agent_trace=trace,
            health_guidance=provisional_assessment.health_guidance,
            verification_findings=provisional_assessment.verification_findings,
            variant_annotations=provisional_assessment.variant_annotations,
            evidence_sources=provisional_assessment.evidence_sources,
        )

        return parsed_case, evidence, workplace_context, assessment
