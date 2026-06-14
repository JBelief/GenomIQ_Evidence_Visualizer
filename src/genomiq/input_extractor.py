from __future__ import annotations

import re


KNOWN_MARKERS = {
    "BRCA1": "BRCA1_mut",
    "BRCA2": "BRCA2_mut",
    "BRAF": "BRAF_V600E",
    "V600E": "BRAF_V600E",
    "PARP": "PARP_pathway_dependency",
    "TP53": "TP53_mut",
    "MSH2": "MSH2_mut",
    "MLH1": "MLH1_mut",
}

COORDINATE_PATTERN = re.compile(
    r"\bchr(?:omosome)?\s*([0-9XYM]{1,2})\s*:\s*(\d{2,12})(?:\s*[:\s]\s*([ACGTN-]+)\s*>\s*([ACGTN-]+))?\b",
    re.IGNORECASE,
)
HGVS_GENOMIC_PATTERN = re.compile(
    r"\bchr(?:omosome)?\s*([0-9XYM]{1,2})\s*:\s*g\.\s*(\d{2,12})\s*([ACGTN-]+)\s*>\s*([ACGTN-]+)\b",
    re.IGNORECASE,
)
VCF_CHROMOSOMES = {str(item) for item in range(1, 23)} | {"X", "Y", "M", "MT"}


def extract_variant_markers(text: str) -> list[str]:
    """Extract variant markers from free text, coordinate snippets, and VCF rows."""

    upper_text = text.upper()
    markers = {value for key, value in KNOWN_MARKERS.items() if key in upper_text}

    for match in COORDINATE_PATTERN.finditer(text):
        markers.add(_format_coordinate_marker(match.group(1), match.group(2), match.group(3), match.group(4)))

    for match in HGVS_GENOMIC_PATTERN.finditer(text):
        markers.add(_format_coordinate_marker(match.group(1), match.group(2), match.group(3), match.group(4)))

    for line in text.splitlines():
        marker = _extract_vcf_marker(line)
        if marker:
            markers.add(marker)

    return sorted(markers)


def _extract_vcf_marker(line: str) -> str | None:
    if not line or line.startswith("#"):
        return None

    columns = line.strip().split()
    if len(columns) < 5:
        return None

    chrom, pos, _variant_id, ref, alt = columns[:5]
    normalized_chrom = chrom.removeprefix("chr").removeprefix("CHR").upper()
    if normalized_chrom not in VCF_CHROMOSOMES:
        return None
    if not pos.isdigit():
        return None
    if not re.fullmatch(r"[ACGTN.]+", ref.upper()):
        return None
    first_alt = alt.split(",")[0].upper()
    if not re.fullmatch(r"[ACGTN.]+", first_alt):
        return None

    return _format_coordinate_marker(normalized_chrom, pos, ref.upper(), first_alt)


def _format_coordinate_marker(chromosome: str, position: str, reference: str | None, alternate: str | None) -> str:
    chromosome = chromosome.upper()
    if chromosome == "MT":
        chromosome = "M"
    if reference and alternate:
        return f"chr{chromosome}:{position}:{reference.upper()}>{alternate.upper()}"
    return f"chr{chromosome}:{position}"
