from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass(frozen=True)
class PubMedRecord:
    pmid: str
    title: str
    source: str
    pubdate: str
    url: str


@dataclass(frozen=True)
class SeedRecord:
    variant: str
    gene: str
    disease_area: str
    coordinate_hint: str
    known_rsid_hint: str
    pubmed_query: str
    dbsnp_query: str


def load_seed_records(path: Path) -> list[SeedRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [SeedRecord(**item) for item in payload]


def ncbi_json(endpoint: str, params: dict[str, str], *, timeout: int = 10) -> dict[str, Any]:
    api_key = os.environ.get("NCBI_API_KEY")
    request_params = dict(params)
    request_params["tool"] = "genomiq"
    request_params["email"] = os.environ.get("NCBI_EMAIL", "anonymous@example.com")
    if api_key:
        request_params["api_key"] = api_key

    delay = 0.1 if api_key else 0.34
    time.sleep(delay)
    url = f"{NCBI_BASE}/{endpoint}?" + urlencode(request_params)
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def search_pubmed(query: str, retmax: int) -> list[str]:
    payload = ncbi_json(
        "esearch.fcgi",
        {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": str(retmax),
            "sort": "relevance",
        },
    )
    return payload.get("esearchresult", {}).get("idlist", [])


def summarize_pubmed(pmids: list[str]) -> list[PubMedRecord]:
    if not pmids:
        return []
    payload = ncbi_json(
        "esummary.fcgi",
        {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
        },
    )
    result = payload.get("result", {})
    records: list[PubMedRecord] = []
    for pmid in result.get("uids", []):
        item = result.get(pmid, {})
        records.append(
            PubMedRecord(
                pmid=pmid,
                title=item.get("title", "PubMed result without title"),
                source=item.get("source", "PubMed"),
                pubdate=item.get("pubdate", "date unavailable"),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            )
        )
    return records


def search_dbsnp(query: str, retmax: int) -> list[str]:
    payload = ncbi_json(
        "esearch.fcgi",
        {
            "db": "snp",
            "term": query,
            "retmode": "json",
            "retmax": str(retmax),
            "sort": "relevance",
        },
    )
    ids = payload.get("esearchresult", {}).get("idlist", [])
    return [f"rs{item}" if not str(item).startswith("rs") else str(item) for item in ids]


def render_markdown(
    seed_records: list[SeedRecord],
    pubmed_by_variant: dict[str, list[PubMedRecord]],
    dbsnp_by_variant: dict[str, list[str]],
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# GenomIQ NCBI Variant Evidence RAG Dataset",
        "",
        f"Generated at: {generated_at}",
        "",
        "Purpose: uploadable research-only knowledge source for Microsoft Foundry IQ or local RAG demos.",
        "",
        "Safety boundary: this dataset contains public NCBI/PubMed metadata only. It is not a clinical guideline, diagnostic source, treatment recommendation, or patient-specific interpretation.",
        "",
        "Scoring guidance: disease association scores in GenomIQ should treat these records as evidence candidates. A variant-disease claim still requires coordinate normalization, citation review, and human approval.",
        "",
    ]

    for seed in seed_records:
        dbsnp_ids = dbsnp_by_variant.get(seed.variant, [])
        pubmed_records = pubmed_by_variant.get(seed.variant, [])
        lines.extend(
            [
                f"## {seed.variant}",
                "",
                f"- Gene: {seed.gene}",
                f"- Disease area: {seed.disease_area}",
                f"- Coordinate hint: {seed.coordinate_hint or 'not specified'}",
                f"- Curated rsID hint: {seed.known_rsid_hint or 'not specified'}",
                f"- NCBI dbSNP candidates: {', '.join(dbsnp_ids) if dbsnp_ids else 'none retrieved'}",
                f"- PubMed query: `{seed.pubmed_query}`",
                "",
                "### PubMed Evidence Candidates",
                "",
            ]
        )
        if pubmed_records:
            for record in pubmed_records:
                lines.extend(
                    [
                        f"- PMID:{record.pmid} | {record.title}",
                        f"  - Source: {record.source}; publication date: {record.pubdate}",
                        f"  - URL: {record.url}",
                    ]
                )
        else:
            lines.append("- No PubMed records retrieved for this seed query.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_dataset(seed_path: Path, output_path: Path, retmax: int, offline: bool = False) -> str:
    seed_records = load_seed_records(seed_path)
    pubmed_by_variant: dict[str, list[PubMedRecord]] = {}
    dbsnp_by_variant: dict[str, list[str]] = {}

    if not offline:
        for seed in seed_records:
            try:
                pmids = search_pubmed(seed.pubmed_query, retmax)
                pubmed_by_variant[seed.variant] = summarize_pubmed(pmids)
            except OSError:
                pubmed_by_variant[seed.variant] = []

            try:
                dbsnp_by_variant[seed.variant] = search_dbsnp(seed.dbsnp_query, retmax)
            except OSError:
                dbsnp_by_variant[seed.variant] = []

    markdown = render_markdown(seed_records, pubmed_by_variant, dbsnp_by_variant)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a no-cost NCBI/PubMed RAG dataset for GenomIQ.")
    parser.add_argument("--seed", default="knowledge/variant_seed_queries.json", help="Path to seed query JSON.")
    parser.add_argument("--out", default="knowledge/ncbi_variant_rag_dataset.md", help="Output markdown path.")
    parser.add_argument("--retmax", type=int, default=3, help="Maximum records per NCBI query.")
    parser.add_argument("--offline", action="store_true", help="Render the dataset template without live NCBI calls.")
    args = parser.parse_args()

    build_dataset(Path(args.seed), Path(args.out), args.retmax, offline=args.offline)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
