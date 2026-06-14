# GenomIQ Demo Knowledge Base

This file is synthetic demo content for Microsoft Foundry IQ grounding. It contains no patient data, PHI, PII, secrets, or confidential workplace data.

## PMCID:DEMO-BRCA-PARP-001

Title: Synthetic demo summary of BRCA deficiency and PARP pathway vulnerability

Research-only summary:

BRCA1/2-deficient tumor models are commonly used as a research example for PARP inhibitor vulnerability. This relationship is useful for precision oncology evidence review and research triage, but it must not be presented as an individual diagnosis, treatment recommendation, or clinical decision.

Supported demo markers:

- BRCA1_mut
- BRCA2_mut
- PARP_pathway_dependency

Safety language:

Any response based on this evidence must state that it is research-only and not a treatment recommendation.

## PMCID:DEMO-BRCA2-002

Title: Synthetic demo summary of homologous recombination pathway disruption

Research-only summary:

BRCA2 pathway disruption may be relevant to homologous recombination research workflows. Confidence should remain moderate unless additional grounded sources are available.

Supported demo markers:

- BRCA2_mut
- homologous_recombination_deficiency

Safety language:

This evidence supports research review only. It does not establish diagnosis or therapy selection.

## GenomIQ Safety Policy

The GenomIQ Evidence Visualizer should:

1. Use only de-identified or synthetic research cases in the public demo.
2. Attach citation IDs to research claims.
3. Decline to provide diagnosis or treatment recommendations.
4. Require human review before report export.
5. Block output if the request includes patient identifiers, secrets, or confidential workplace data.

