# GenomIQ Evidence Visualizer Demo Script

Target length: 2-3 minutes

## 0:00-0:20 Opening

"GenomIQ Evidence Visualizer is a research-grade multi-agent assistant for genomic variant evidence review. It is not a diagnosis tool and does not provide treatment recommendations."

"The project shows a Foundry Agent calling a custom OpenAPI tool that runs a deterministic GenomIQ backend: variant normalization, MCP-based annotation, NCBI/PubMed source interpretation, verification, human approval, and interactive report generation."

## 0:20-0:45 Foundry Agent And Tool Call

Show the Foundry Agent Playground with the OpenAPI tool configured.

Prompt:

```text
Use the generate_genomiq_report tool.

case_text:
Synthetic de-identified VCF-like input:
#CHROM POS ID REF ALT QUAL FILTER INFO
7 182734 . A G 100 PASS .
Additional marker: BRCA1

use_ncbi_live: true
use_pubmed_live: true
approved_for_export: true

Return parsed variants, dbSNP IDs, PubMed IDs, verification findings, and the report URL.
```

Narration:

"The Foundry Agent is the research-facing reasoning interface. The custom OpenAPI tool calls the local GenomIQ backend through a temporary HTTPS tunnel."

## 0:45-1:15 Source Interpretation Result

Show the Playground tool response or terminal logs.

Point out:

- Parsed variants: `BRCA1_mut`, `chr7:182734:A>G`
- dbSNP IDs such as `rs80357906`, `rs2534492024`
- PubMed IDs returned by live PubMed E-utilities
- Verification status and report URL

Narration:

"The backend does not invent a disease claim from raw coordinates. It extracts the coordinate, checks dbSNP, retrieves PubMed metadata, and carries those source identifiers into the report."

## 1:15-1:55 Interactive Report

Open the `report_url`.

Show:

- Summary tab: top disease vulnerability hypotheses and input variant badges
- Evidence tab: variant annotation, dbSNP IDs, PubMed titles and URLs
- Reasoning tab: multi-agent trace
- Safety tab: PHI/PII, annotation, citation, confidence checks
- Human approval toggle

Narration:

"The final output is a single-file interactive HTML report. It shows not only the conclusion, but also the source IDs, reasoning trace, verification findings, and human review state."

## 1:55-2:25 Local Reliability Demo

Show terminal command if time allows:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Optional CLI demo:

```bash
PYTHONPATH=src python3 -m genomiq.orchestrator \
  --case examples/vcf_coordinate_case.txt \
  --auto-approve \
  --use-ncbi-live \
  --use-pubmed-live
```

Narration:

"The same workflow can run locally without paid web search or real workplace data. The public demo uses synthetic inputs and avoids PHI, PII, secrets, and confidential data."

## 2:25-2:45 Close

"GenomIQ demonstrates a safe enterprise-agent pattern for precision oncology research: Foundry Agent orchestration, custom tools, local MCP annotation, source-grounded evidence, verification gates, and human-approved report export."
