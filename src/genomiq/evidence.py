from __future__ import annotations

import json
import os
import time
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import urlopen

from genomiq.schema import EvidenceSource, ParsedCase


class EvidenceRetriever(Protocol):
    def retrieve(self, parsed_case: ParsedCase) -> list[EvidenceSource]:
        """Return grounded evidence records with stable document IDs."""


class DemoFoundryIQEvidenceRetriever:
    """Foundry IQ-style retriever backed by a synthetic, citation-ready catalog."""

    def retrieve(self, parsed_case: ParsedCase) -> list[EvidenceSource]:
        markers = set(parsed_case.variants)
        evidence: list[EvidenceSource] = []

        if {"BRCA1_mut", "PARP_pathway_dependency"} <= markers:
            evidence.append(
                EvidenceSource(
                    doc_id="PMCID:DEMO-BRCA-PARP-001",
                    title="Synthetic demo summary of BRCA deficiency and PARP inhibitor sensitivity",
                    source_type="demo_pubmed_abstract",
                    summary=(
                        "BRCA1/2-deficient tumor models are commonly used as a research example "
                        "for PARP inhibitor vulnerability; this supports research triage, not diagnosis."
                    ),
                    confidence=0.86,
                    url="https://pubmed.ncbi.nlm.nih.gov/",
                )
            )

        if "BRCA2_mut" in markers:
            evidence.append(
                EvidenceSource(
                    doc_id="PMCID:DEMO-BRCA2-002",
                    title="Synthetic demo summary of BRCA2 pathway disruption",
                    source_type="demo_pubmed_abstract",
                    summary="BRCA2 disruption may be relevant to homologous recombination research workflows.",
                    confidence=0.74,
                    url="https://pubmed.ncbi.nlm.nih.gov/",
                )
            )

        if "BRAF_V600E" in markers or "chr7:140753336:A>T" in markers:
            evidence.append(
                EvidenceSource(
                    doc_id="PMCID:DEMO-BRAF-V600E-CRC",
                    title="Synthetic demo grounding for BRAF V600E in colorectal cancer research",
                    source_type="demo_pubmed_abstract",
                    summary=(
                        "BRAF V600E is a recurrent MAPK pathway hotspot commonly discussed in colorectal "
                        "cancer molecular stratification literature; this supports research review only."
                    ),
                    confidence=0.82,
                    url="https://pubmed.ncbi.nlm.nih.gov/?term=BRAF+V600E+colorectal+cancer",
                )
            )

        if not evidence:
            evidence.append(
                EvidenceSource(
                    doc_id="GENOMIQ:INSUFFICIENT-EVIDENCE",
                    title="No high-confidence demo evidence match",
                    source_type="safety_gate",
                    summary="The demo evidence catalog did not find enough grounded support for a visual risk claim.",
                    confidence=0.25,
                )
            )

        return evidence


class PubMedEvidenceRetriever:
    """Optional no-Bing literature retriever using NCBI E-utilities.

    This provides a low-cost source interpretation path for hackathon demos.
    It is disabled by default so tests and public judging remain deterministic.
    NCBI allows unauthenticated E-utilities calls with conservative rate limits;
    set NCBI_API_KEY only in the local environment if higher limits are needed.
    """

    def retrieve(self, parsed_case: ParsedCase) -> list[EvidenceSource]:
        query = self._build_query(parsed_case)
        ids = self._esearch(query)
        if not ids:
            return []
        return self._esummary(ids[:3])

    def _build_query(self, parsed_case: ParsedCase) -> str:
        marker_terms = []
        for marker in parsed_case.variants:
            if marker.startswith("chr"):
                continue
            marker_terms.append(
                marker.replace("_mut", "")
                .replace("_pathway_dependency", "")
                .replace("_", " ")
            )
        marker_query = " AND ".join(sorted(set(marker_terms))) or "genomic variant"
        return f"({marker_query}) AND ({parsed_case.primary_research_area})"

    def _esearch(self, query: str) -> list[str]:
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": "3",
            "sort": "relevance",
            "tool": "genomiq",
        }
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            params["api_key"] = api_key

        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urlencode(params)
        try:
            time.sleep(0.34 if not api_key else 0.1)
            with urlopen(url, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except OSError:
            return []
        return payload.get("esearchresult", {}).get("idlist", [])

    def _esummary(self, pmids: list[str]) -> list[EvidenceSource]:
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
            "tool": "genomiq",
        }
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            params["api_key"] = api_key

        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + urlencode(params)
        try:
            time.sleep(0.34 if not api_key else 0.1)
            with urlopen(url, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except OSError:
            return []

        result = payload.get("result", {})
        evidence: list[EvidenceSource] = []
        for pmid in result.get("uids", []):
            item = result.get(pmid, {})
            title = item.get("title", "PubMed result without title")
            source = item.get("source", "PubMed")
            pubdate = item.get("pubdate", "date unavailable")
            evidence.append(
                EvidenceSource(
                    doc_id=f"PMID:{pmid}",
                    title=title,
                    source_type="pubmed_esummary",
                    summary=f"{source}; publication date: {pubdate}. Live PubMed summary metadata only.",
                    confidence=0.72,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                )
            )
        return evidence


class CompositeEvidenceRetriever:
    def __init__(self, retrievers: list[EvidenceRetriever]) -> None:
        self.retrievers = retrievers

    def retrieve(self, parsed_case: ParsedCase) -> list[EvidenceSource]:
        merged: list[EvidenceSource] = []
        seen: set[str] = set()
        for retriever in self.retrievers:
            for item in retriever.retrieve(parsed_case):
                if item.doc_id not in seen:
                    seen.add(item.doc_id)
                    merged.append(item)
        return merged


class AzureFoundryIQEvidenceRetriever:
    """Optional Azure Foundry-backed retriever.

    This adapter is intentionally imported lazily so the offline demo and tests do not
    require Azure packages. In a real hackathon environment, configure a Foundry
    project agent that has Foundry IQ knowledge attached, then set:

    - GENOMIQ_USE_AZURE_FOUNDRY=true
    - PROJECT_ENDPOINT=https://...
    - GENOMIQ_FOUNDRY_AGENT_NAME=...
    """

    def __init__(self) -> None:
        self.project_endpoint = os.environ.get("PROJECT_ENDPOINT", "")
        self.agent_name = os.environ.get("GENOMIQ_FOUNDRY_AGENT_NAME", "")

        if not self.project_endpoint or not self.agent_name:
            raise RuntimeError("PROJECT_ENDPOINT and GENOMIQ_FOUNDRY_AGENT_NAME are required for Azure Foundry IQ.")

        try:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential
        except ImportError as exc:
            raise RuntimeError(
                "Azure Foundry integration requires azure-ai-projects and azure-identity. "
                "Install optional Azure dependencies before enabling GENOMIQ_USE_AZURE_FOUNDRY."
            ) from exc

        credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        )
        self.project_client = AIProjectClient(credential=credential, endpoint=self.project_endpoint)
        self.openai_client = self.project_client.get_openai_client()
        self.agent = self.project_client.agents.get(agent_name=self.agent_name)

    def retrieve(self, parsed_case: ParsedCase) -> list[EvidenceSource]:
        prompt = (
            "Search the attached Foundry IQ knowledge base for research evidence about these markers: "
            f"{', '.join(parsed_case.variants)}. "
            "Return a concise research-only summary with citation IDs. "
            "Do not provide diagnosis or treatment recommendations."
        )

        conversation = self.openai_client.conversations.create(
            items=[{"type": "message", "role": "user", "content": prompt}]
        )
        response = self.openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
            input="",
        )

        output_text = getattr(response, "output_text", "") or str(response)
        doc_id = "FOUNDRY-IQ:AGENT-CITED-EVIDENCE"
        confidence = 0.78 if output_text else 0.35

        return [
            EvidenceSource(
                doc_id=doc_id,
                title="Azure Foundry IQ agent evidence response",
                source_type="azure_foundry_iq",
                summary=output_text[:1200] if output_text else "No Foundry IQ evidence text was returned.",
                confidence=confidence,
            )
        ]


def build_evidence_retriever() -> EvidenceRetriever:
    use_azure_foundry = os.environ.get("GENOMIQ_USE_AZURE_FOUNDRY", "false").lower() == "true"
    use_pubmed_live = os.environ.get("GENOMIQ_USE_PUBMED_LIVE", "false").lower() == "true"
    if use_azure_foundry:
        return AzureFoundryIQEvidenceRetriever()
    if use_pubmed_live:
        return CompositeEvidenceRetriever([DemoFoundryIQEvidenceRetriever(), PubMedEvidenceRetriever()])
    return DemoFoundryIQEvidenceRetriever()
