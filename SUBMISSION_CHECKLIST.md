# Submission Checklist

## Repository

- [ ] Public GitHub repository created.
- [ ] `.env` is not committed.
- [ ] No secrets, API keys, connection strings, PHI, PII, or confidential workplace data are committed.
- [ ] `artifacts/` remains ignored; reports can be regenerated.
- [ ] `assets/clinical_body_template.png` is included and appropriate for public demo use.
- [ ] README explains Foundry Agent, OpenAPI tool, MCP server, NCBI/PubMed source interpretation, verification, HITL, and report generation.

## Validation

- [ ] Run static compile:

```bash
PYTHONPATH=src python3 -m py_compile src/genomiq/*.py api_server.py mcp_servers/genomiq_variant_server.py
```

- [ ] Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

- [ ] Run offline demo:

```bash
PYTHONPATH=src python3 -m genomiq.orchestrator --case examples/synthetic_case.txt --auto-approve
```

- [ ] Run live NCBI/PubMed demo:

```bash
PYTHONPATH=src python3 -m genomiq.orchestrator \
  --case examples/vcf_coordinate_case.txt \
  --auto-approve \
  --use-ncbi-live \
  --use-pubmed-live
```

- [ ] Start API server:

```bash
PYTHONPATH=src python3 api_server.py
```

- [ ] Start tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

- [ ] Confirm Foundry OpenAPI tool can call `generate_genomiq_report`.
- [ ] Confirm returned `report_url` opens the interactive HTML report.

## Demo Video

- [ ] State clearly: "This is not a diagnosis or treatment recommendation tool."
- [ ] Show Foundry Agent Playground and OpenAPI tool call.
- [ ] Show parsed variants, dbSNP IDs, PubMed IDs, and verification findings.
- [ ] Open the generated report URL.
- [ ] Show Evidence, Reasoning, and Safety tabs.
- [ ] Show human approval state.
- [ ] Mention synthetic/de-identified input and no committed secrets/PHI/PII.
- [ ] Mention cost-safe design: no paid Bing Grounding, no required Azure AI Search, no real M365 data.

## Submission Text

Suggested short description:

> GenomIQ Evidence Visualizer is a research-grade multi-agent genomic variant evidence assistant that connects Microsoft Foundry Agents to a custom OpenAPI backend, local MCP variant annotation, NCBI/PubMed source interpretation, verification gates, human approval, and an interactive HTML report.
