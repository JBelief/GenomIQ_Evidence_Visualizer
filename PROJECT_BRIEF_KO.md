# GenomIQ Evidence Visualizer 기획안

## 한 줄 설명

GenomIQ Evidence Visualizer는 합성 또는 비식별 genomic variant 입력을 받아 변이 정규화, MCP 기반 annotation, NCBI/PubMed source interpretation, 검증, human approval, interactive HTML report 생성을 수행하는 연구용 멀티 에이전트 시스템입니다.

본 프로젝트는 진단 또는 치료 추천 도구가 아니라 **정밀 종양학 연구 근거 검토 보조 도구**입니다.

## 해카톤 적합성

Challenge: **Reasoning Agents / Enterprise Agents**

핵심 충족 요소:

- Microsoft Foundry Agent와 Custom OpenAPI tool 연동
- 여러 전문 agent의 multi-step reasoning trace
- no-cost local MCP stdio server를 통한 `annotate_variant` tool 제공
- NCBI E-utilities 기반 dbSNP/PubMed source interpretation
- PHI/PII, citation, confidence, annotation coverage verification
- Human-in-the-loop 승인 후 report export
- Interactive single-file HTML report
- synthetic/de-identified demo data와 no-secret public repo 구성

Microsoft IQ 관련 포지션:

- 공개 데모는 비용과 데이터 거버넌스를 위해 유료 Foundry IQ/Azure AI Search 없이 실행됩니다.
- evidence retrieval interface는 승인된 환경에서 Foundry IQ knowledge source로 교체/확장 가능합니다.
- Work IQ/M365 실제 데이터는 tenant/admin/license 제약이 있으므로 public demo에서는 synthetic permission-scoped adapter로 표현합니다.

## 최종 사용자 시나리오

1. 연구자가 Foundry Playground 또는 CLI에 synthetic/de-identified variant input을 입력합니다.
2. Foundry Agent가 연구용 reasoning과 safety boundary를 유지하며 `generate_genomiq_report` OpenAPI tool을 호출합니다.
3. GenomIQ backend가 free text, coordinate, VCF-like row에서 variant marker를 추출합니다.
4. Variant Annotation Agent가 local MCP tool boundary를 통해 coordinate, allele, gene, dbSNP 정보를 구조화합니다.
5. NCBI Source Interpretation Agent가 dbSNP rsID와 PubMed PMID/title/URL metadata를 수집합니다.
6. Disease Network Reasoning Agent가 top vulnerability hypotheses를 ranking합니다.
7. Verification Agent가 PHI/PII, annotation coverage, citation format, evidence confidence를 검증합니다.
8. Safety Reviewer와 human approval gate가 export 가능 여부를 결정합니다.
9. Visual Report Agent가 interactive HTML report와 JSON report를 생성합니다.
10. Foundry Playground는 최종 `report_url`을 반환하고, 사용자는 링크로 report를 확인합니다.

## 심사 기준별 어필 포인트

- Accuracy & Relevance: claim은 citation ID, dbSNP ID, PubMed metadata, confidence threshold와 연결
- Reasoning & Multi-step Thinking: parsing, annotation, source interpretation, disease reasoning, metadata weighting, verification, safety, report가 분리된 trace로 표시
- Creativity & Originality: 변이 근거 검토를 interactive clinical-style report로 변환
- UX & Presentation: Foundry tool call과 report URL 기반 데모 가능
- Reliability & Safety: no secrets, no PHI/PII, synthetic data, confidence gate, citation gate, HITL approval
- Cost Governance: Bing Grounding, Azure AI Search, real M365 data 없이 cost-safe demo 가능

## 데모 포인트

- Foundry Agent가 OpenAPI tool을 호출해 GenomIQ backend 실행
- VCF-like input `chr7:182734:A>G` 추출
- NCBI dbSNP rsID와 PubMed PMID 반환
- Reasoning tab에서 전체 multi-agent trace 확인
- Evidence tab에서 variant annotation, dbSNP ID, PubMed title/URL 확인
- Safety tab에서 verification findings 확인
- Summary에서 top disease vulnerability hypotheses와 organ hotspot 확인

## 발표 시 주의 표현

사용할 표현:

- research-grade evidence assistant
- synthetic/de-identified genomic variant review
- multi-agent reasoning trace
- local MCP stdio server
- NCBI/PubMed source interpretation
- Foundry custom OpenAPI tool
- human-approved interactive report

피해야 할 표현:

- diagnosis
- treatment recommendation
- clinical decision automation
- patient chart integration
- hallucination completely eliminated
- scans all emails
- real patient data
