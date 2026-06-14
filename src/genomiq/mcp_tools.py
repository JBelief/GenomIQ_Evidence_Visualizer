from __future__ import annotations

import json
import os
import re
import time
from urllib.parse import urlencode
from urllib.request import urlopen
from dataclasses import dataclass

from genomiq.schema import VariantAnnotation


@dataclass(frozen=True)
class MCPToolCall:
    server_label: str
    tool_name: str
    arguments: dict[str, str]


class VariantAnnotationMCPTool:
    """MCP-style local tool adapter for cost-safe variant annotation demos.

    In a production version this boundary can be replaced with a real MCP server
    backed by Ensembl VEP, NCBI variation services, or an internal annotation API.
    """

    server_label = "genomiq-variant-mcp"
    tool_name = "annotate_variant"
    coordinate_pattern = re.compile(r"^chr([0-9XYM]{1,2}):(\d{2,12})(?::([ACGTN.-]+)>([ACGTN.-]+))?$", re.IGNORECASE)

    _catalog = {
        "BRCA1_mut": VariantAnnotation(
            variant="BRCA1_mut",
            chromosome="17",
            coordinate="17:43044295",
            reference="G",
            alternate="A",
            gene_name="BRCA1",
            gene_id="ENSG00000012048",
            dbsnp_id="rs80357906",
            consequence="loss_of_function_demo",
        ),
        "BRCA2_mut": VariantAnnotation(
            variant="BRCA2_mut",
            chromosome="13",
            coordinate="13:32316461",
            reference="C",
            alternate="T",
            gene_name="BRCA2",
            gene_id="ENSG00000139618",
            dbsnp_id="rs80359550",
            consequence="homologous_recombination_demo",
        ),
        "PARP_pathway_dependency": VariantAnnotation(
            variant="PARP_pathway_dependency",
            chromosome="1",
            coordinate="1:226366560",
            reference="pathway",
            alternate="dependency",
            gene_name="PARP1",
            gene_id="ENSG00000143799",
            dbsnp_id="pathway-marker-demo",
            consequence="dna_repair_pathway_dependency_demo",
        ),
        "TP53_mut": VariantAnnotation(
            variant="TP53_mut",
            chromosome="17",
            coordinate="17:7674220",
            reference="C",
            alternate="T",
            gene_name="TP53",
            gene_id="ENSG00000141510",
            dbsnp_id="rs1042522",
            consequence="tumor_suppressor_demo",
        ),
        "BRAF_V600E": VariantAnnotation(
            variant="BRAF_V600E",
            chromosome="7",
            coordinate="7:140753336",
            reference="A",
            alternate="T",
            gene_name="BRAF",
            gene_id="ENSG00000157764",
            dbsnp_id="rs113488022",
            consequence="p.V600E_demo_oncogenic_hotspot",
        ),
        "chr7:140753336:A>T": VariantAnnotation(
            variant="chr7:140753336:A>T",
            chromosome="7",
            coordinate="7:140753336",
            reference="A",
            alternate="T",
            gene_name="BRAF",
            gene_id="ENSG00000157764",
            dbsnp_id="rs113488022",
            consequence="BRAF_V600E_coordinate_demo_match",
        ),
    }

    def build_call(self, variant: str) -> MCPToolCall:
        return MCPToolCall(
            server_label=self.server_label,
            tool_name=self.tool_name,
            arguments={"variant": variant},
        )

    def annotate(self, variant: str) -> VariantAnnotation:
        if variant in self._catalog:
            return self._catalog[variant]
        if self.coordinate_pattern.match(variant):
            live_annotation = self._annotate_coordinate_with_ncbi(variant)
            if live_annotation is not None:
                return live_annotation
            chromosome, coordinate = self._split_coordinate(variant)
            reference, alternate = self._split_alleles(variant)
            return VariantAnnotation(
                variant=variant,
                chromosome=chromosome,
                coordinate=coordinate,
                reference=reference,
                alternate=alternate,
                gene_name="requires_live_annotation",
                gene_id="requires_live_annotation",
                dbsnp_id="requires_live_ncbi_lookup",
                consequence="coordinate_marker_requires_ncbi_or_vep_lookup",
            )
        return VariantAnnotation(
            variant=variant,
            chromosome="unknown",
            coordinate="unknown",
            reference="unknown",
            alternate="unknown",
            gene_name="unknown",
            gene_id="unknown",
            dbsnp_id="unknown",
            consequence="unresolved_demo_marker",
        )

    def _annotate_coordinate_with_ncbi(self, variant: str) -> VariantAnnotation | None:
        use_live_ncbi = os.environ.get("GENOMIQ_USE_NCBI_LIVE", "false").lower() == "true"
        if not use_live_ncbi:
            return None

        chromosome, coordinate = self._split_coordinate(variant)
        params = {
            "db": "snp",
            "term": f"{chromosome}[CHR] AND {coordinate}[CHRPOS]",
            "retmode": "json",
            "retmax": "1",
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
            return None

        ids = payload.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return None

        return VariantAnnotation(
            variant=variant,
            chromosome=chromosome,
            coordinate=coordinate,
            reference=self._split_alleles(variant)[0],
            alternate=self._split_alleles(variant)[1],
            gene_name="pending_gene_mapping",
            gene_id="pending_gene_mapping",
            dbsnp_id=f"rs{ids[0]}",
            consequence=(
                f"NCBI dbSNP ESearch coordinate match for chromosome {chromosome} "
                f"position {coordinate.split(':', 1)[1]}; gene mapping remains pending."
            ),
        )

    def _split_coordinate(self, variant: str) -> tuple[str, str]:
        match = self.coordinate_pattern.match(variant)
        if not match:
            return "unknown", "unknown"
        chromosome = match.group(1).upper()
        coordinate = match.group(2)
        return chromosome, f"{chromosome}:{coordinate}"

    def _split_alleles(self, variant: str) -> tuple[str, str]:
        match = self.coordinate_pattern.match(variant)
        if not match:
            return "unknown", "unknown"
        reference = match.group(3)
        alternate = match.group(4)
        return reference.upper() if reference else "unknown", alternate.upper() if alternate else "unknown"
