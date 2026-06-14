from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RiskTier(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ClaimStatus(str, Enum):
    SUPPORTED = "supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ParsedCase:
    variants: list[str]
    confidence_score: float
    primary_research_area: str
    contains_sensitive_identifiers: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        if not self.variants:
            raise ValueError("at least one variant or pathway marker is required")


@dataclass(frozen=True)
class EvidenceSource:
    doc_id: str
    title: str
    source_type: str
    summary: str
    confidence: float
    url: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("evidence confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class WorkplaceContext:
    context_id: str
    source_label: str
    summary: str
    approved_for_demo: bool


@dataclass(frozen=True)
class DemographicMetadata:
    sex: str
    age: int
    height_cm: float
    weight_kg: float
    known_conditions: list[str] = field(default_factory=list)
    family_history: list[str] = field(default_factory=list)

    @property
    def bmi(self) -> float:
        height_m = self.height_cm / 100
        return round(self.weight_kg / (height_m * height_m), 1)


@dataclass(frozen=True)
class VariantAnnotation:
    variant: str
    chromosome: str
    coordinate: str
    reference: str
    alternate: str
    gene_name: str
    gene_id: str
    dbsnp_id: str
    consequence: str


@dataclass(frozen=True)
class DiseaseHypothesis:
    disease: str
    score: float
    risk_genes: list[str]
    variant_ids: list[str]
    rationale: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("disease score must be between 0.0 and 1.0")


@dataclass(frozen=True)
class AgentTraceStep:
    agent_name: str
    action: str
    output_summary: str


@dataclass(frozen=True)
class VerificationFinding:
    level: str
    check_name: str
    detail: str


@dataclass(frozen=True)
class RiskAssessment:
    tier: RiskTier
    organ: str
    confidence: float
    claim_status: ClaimStatus
    rationale: str
    evidence_ids: list[str] = field(default_factory=list)
    workplace_context_ids: list[str] = field(default_factory=list)
    blocked_reasons: list[str] = field(default_factory=list)
    parsed_variants: list[str] = field(default_factory=list)
    top_diseases: list[DiseaseHypothesis] = field(default_factory=list)
    agent_trace: list[AgentTraceStep] = field(default_factory=list)
    health_guidance: list[str] = field(default_factory=list)
    verification_findings: list[VerificationFinding] = field(default_factory=list)
    variant_annotations: list[VariantAnnotation] = field(default_factory=list)
    evidence_sources: list[EvidenceSource] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tier"] = self.tier.value
        data["claim_status"] = self.claim_status.value
        return data


@dataclass(frozen=True)
class VisualReport:
    title: str
    assessment: RiskAssessment
    html_path: str
    json_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "assessment": self.assessment.to_dict(),
            "html_path": self.html_path,
            "json_path": self.json_path,
        }
