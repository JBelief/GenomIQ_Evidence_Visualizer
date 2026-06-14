from __future__ import annotations

import base64
import json
from html import escape
from pathlib import Path

from genomiq.schema import RiskAssessment, RiskTier, VisualReport


TIER_COLORS = {
    RiskTier.LOW: "#d6a80f",
    RiskTier.MEDIUM: "#d96c18",
    RiskTier.HIGH: "#c92f4f",
}


def _js_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True)


def _asset_data_uri(filename: str) -> str:
    asset_path = Path(__file__).resolve().parents[2] / "assets" / filename
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


HOTSPOT_LAYOUTS = {
    "Breast": {
        "label": "Breast",
        "left": "19.4%",
        "top": "28.0%",
        "width": "154px",
        "height": "54px",
        "callout_left": "calc(19.4% + 144px)",
        "callout_top": "calc(28.0% + 18px)",
        "rotation": "-3deg",
    },
    "Ovary": {
        "label": "Ovary",
        "left": "21.2%",
        "top": "43.2%",
        "width": "128px",
        "height": "52px",
        "callout_left": "calc(21.2% + 118px)",
        "callout_top": "calc(43.2% + 18px)",
        "rotation": "-6deg",
    },
    "Stomach": {
        "label": "Stomach",
        "left": "20.2%",
        "top": "36.0%",
        "width": "138px",
        "height": "54px",
        "callout_left": "calc(20.2% + 128px)",
        "callout_top": "calc(36.0% + 18px)",
        "rotation": "-5deg",
    },
    "Colon": {
        "label": "Colon",
        "left": "20.2%",
        "top": "42.0%",
        "width": "138px",
        "height": "54px",
        "callout_left": "calc(20.2% + 128px)",
        "callout_top": "calc(42.0% + 18px)",
        "rotation": "-6deg",
    },
    "General": {
        "label": "General",
        "left": "20.6%",
        "top": "42.8%",
        "width": "128px",
        "height": "56px",
        "callout_left": "calc(20.6% + 118px)",
        "callout_top": "calc(42.8% + 19px)",
        "rotation": "-6deg",
    },
}


def _hotspot_names(organ: str) -> list[str]:
    if "/" in organ:
        names = [item.strip() for item in organ.split("/") if item.strip()]
        return [name for name in names if name in HOTSPOT_LAYOUTS] or ["General"]
    return [organ] if organ in HOTSPOT_LAYOUTS else ["General"]


def _render_hotspots(organ: str) -> str:
    names = _hotspot_names(organ)
    parts: list[str] = []
    for index, name in enumerate(names):
        layout = HOTSPOT_LAYOUTS[name]
        active_class = " is-active" if index == 0 else ""
        parts.append(
            (
                '<button class="hotspot{active_class}" style="left: {left}; top: {top}; '
                'width: {width}; height: {height};" data-region="organ" type="button" '
                'aria-label="{label} research signal hotspot">{label}</button>'
            ).format(
                active_class=active_class,
                left=layout["left"],
                top=layout["top"],
                width=layout["width"],
                height=layout["height"],
                label=escape(layout["label"]),
            )
        )
        parts.append(
            (
                '<span class="risk-callout" style="left: {left}; top: {top}; '
                'transform: rotate({rotation});" aria-hidden="true"></span>'
            ).format(
                left=layout["callout_left"],
                top=layout["callout_top"],
                rotation=layout["rotation"],
            )
        )
    return "".join(parts)


def write_visual_report(assessment: RiskAssessment, output_dir: Path) -> VisualReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "genomiq_interactive_report.html"
    json_path = output_dir / "genomiq_report.json"

    tier_color = TIER_COLORS[assessment.tier]
    confidence_pct = round(assessment.confidence * 100)
    evidence_ids = assessment.evidence_ids or ["none"]
    context_ids = assessment.workplace_context_ids or ["none"]
    blocked_reasons = assessment.blocked_reasons or ["No blocking safety issues detected in the synthetic demo."]
    parsed_variants = assessment.parsed_variants or ["none"]
    top_diseases = assessment.top_diseases or []
    agent_trace = assessment.agent_trace or []
    health_guidance = assessment.health_guidance or [
        "No wellness guidance was generated for this synthetic case.",
    ]
    verification_findings = assessment.verification_findings or []
    variant_annotations = assessment.variant_annotations or []
    evidence_sources = assessment.evidence_sources or []
    body_template_uri = _asset_data_uri("clinical_body_template.png")
    hotspot_markup = _render_hotspots(assessment.organ)

    disease_rows = "".join(
        (
            '<li><span class="rank">{rank}</span><span><strong>{disease}</strong>'
            '<small>Score {score} | Genes: {genes} | Variants: {variants}</small>'
            '<em>{rationale}</em></span></li>'
        ).format(
            rank=index,
            disease=escape(item.disease),
            score=escape(f"{item.score:.3f}"),
            genes=escape(", ".join(item.risk_genes) or "metadata"),
            variants=escape(", ".join(item.variant_ids) or "metadata-only"),
            rationale=escape(item.rationale),
        )
        for index, item in enumerate(top_diseases, start=1)
    )
    if not disease_rows:
        disease_rows = '<li><span class="rank">-</span><span><strong>No supported hypothesis</strong><small>Score unavailable</small><em>Evidence was insufficient for top-three ranking.</em></span></li>'

    trace_rows = "".join(
        (
            '<li><span class="step-index">{rank}</span><span><strong>{agent}</strong>'
            '<small>{action}</small><em>{summary}</em></span></li>'
        ).format(
            rank=index,
            agent=escape(step.agent_name),
            action=escape(step.action),
            summary=escape(step.output_summary),
        )
        for index, step in enumerate(agent_trace, start=1)
    )
    verification_rows = "".join(
        (
            '<li><span class="dot {level_class}"></span><span><strong>{level} - {check}</strong>'
            '<small>{detail}</small></span></li>'
        ).format(
            level_class="verification-pass" if finding.level == "pass" else "verification-warn" if finding.level == "warn" else "verification-block",
            level=escape(finding.level.upper()),
            check=escape(finding.check_name),
            detail=escape(finding.detail),
        )
        for finding in verification_findings
    )
    annotation_rows = "".join(
        (
            '<li><span class="dot"></span><span><strong>{variant}</strong>'
            '<small>{coordinate} | {ref}>{alt} | gene: {gene} | dbSNP: {dbsnp}</small>'
            '<em>{consequence}</em></span></li>'
        ).format(
            variant=escape(item.variant),
            coordinate=escape(item.coordinate),
            ref=escape(item.reference),
            alt=escape(item.alternate),
            gene=escape(item.gene_name),
            dbsnp=escape(item.dbsnp_id),
            consequence=escape(item.consequence),
        )
        for item in variant_annotations
    )
    if not annotation_rows:
        annotation_rows = '<li><span class="dot"></span><span>No variant annotation records were produced.</span></li>'

    evidence_rows = "".join(
        (
            '<li><span class="dot"></span><span><strong>{doc_id}</strong>'
            '<small>{title}</small><em>{summary}{url}</em></span></li>'
        ).format(
            doc_id=escape(item.doc_id),
            title=escape(item.title),
            summary=escape(f"{item.source_type}; confidence={item.confidence:.2f}. {item.summary}"),
            url=escape(f" Source: {item.url}" if item.url else ""),
        )
        for item in evidence_sources
    )
    if not evidence_rows:
        evidence_rows = "".join(f'<li><span class="dot"></span><span>{escape(item)}</span></li>' for item in evidence_ids)

    report_payload = {
        "tier": assessment.tier.value,
        "organ": assessment.organ,
        "confidence": assessment.confidence,
        "claimStatus": assessment.claim_status.value,
        "rationale": assessment.rationale,
        "evidenceIds": evidence_ids,
        "workplaceContextIds": context_ids,
        "blockedReasons": blocked_reasons,
        "parsedVariants": parsed_variants,
        "topDiseases": [item.__dict__ for item in top_diseases],
        "agentTrace": [item.__dict__ for item in agent_trace],
        "healthGuidance": health_guidance,
        "verificationFindings": [item.__dict__ for item in verification_findings],
        "variantAnnotations": [item.__dict__ for item in variant_annotations],
        "evidenceSources": [item.__dict__ for item in evidence_sources],
    }

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GenomIQ Evidence Visualizer</title>
  <style>
    :root {{
      --ink: #182033;
      --muted: #647084;
      --paper: #fffdf8;
      --panel: #ffffff;
      --line: #d8dee8;
      --accent: {tier_color};
      --teal: #0d8da8;
      --green: #2e9f78;
      --navy: #15274d;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background: #eceff4;
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
    }}

    .report-shell {{
      width: min(1220px, calc(100vw - 28px));
      min-height: 720px;
      margin: 18px auto;
      background: var(--paper);
      border: 10px solid #a80f1c;
      box-shadow: 0 18px 50px rgba(24, 32, 51, 0.18);
      display: grid;
      grid-template-columns: 560px 1fr;
      gap: 30px;
      padding: 38px 42px;
      position: relative;
      overflow: hidden;
    }}

    .watermark {{
      position: absolute;
      right: 34px;
      bottom: 22px;
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: rgba(100, 112, 132, 0.32);
    }}

    .figure-stage {{
      display: grid;
      grid-template-rows: 1fr auto;
      align-items: center;
      justify-items: center;
      min-width: 0;
    }}

    .body-card {{
      position: relative;
      width: 560px;
      height: 420px;
      border-radius: 18px;
      background: #ffffff;
      border: 1px solid #e0e6ef;
      overflow: hidden;
    }}

    .body-template {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
    }}

    .hotspot {{
      position: absolute;
      border: 4px solid var(--accent);
      border-radius: 999px;
      background: color-mix(in srgb, var(--accent), transparent 64%);
      box-shadow: 0 0 0 8px color-mix(in srgb, var(--accent), transparent 86%), 0 0 24px color-mix(in srgb, var(--accent), transparent 28%);
      color: #ffffff;
      display: grid;
      place-items: center;
      font-weight: 800;
      font-size: 16px;
      text-shadow: 0 1px 8px rgba(0, 0, 0, 0.45);
      cursor: pointer;
      transform-origin: center;
      transition: transform 160ms ease, filter 160ms ease, opacity 160ms ease;
    }}

    .hotspot:hover,
    .hotspot.is-active {{
      transform: scale(1.04);
      filter: saturate(1.1);
    }}

    .risk-callout {{
      position: absolute;
      width: 132px;
      height: 2px;
      background: var(--accent);
      transform-origin: left center;
      opacity: 0.72;
    }}

    .risk-callout::after {{
      content: "Research signal";
      position: absolute;
      left: 132px;
      top: -13px;
      width: 118px;
      color: var(--accent);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.02em;
    }}

    .caption {{
      margin-top: 14px;
      text-align: center;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
    }}

    .content {{
      min-width: 0;
      padding-top: 6px;
    }}

    h1 {{
      margin: 0 0 8px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(34px, 4.4vw, 52px);
      line-height: 1;
      letter-spacing: -0.02em;
      color: #1e1e22;
    }}

    .subtitle {{
      margin: 0 0 26px;
      color: var(--muted);
      font-size: 17px;
      line-height: 1.5;
      max-width: 690px;
    }}

    .status-row {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }}

    .stat {{
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel);
      padding: 14px 16px;
    }}

    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}

    .stat strong {{
      font-size: 22px;
      color: var(--ink);
    }}

    .confidence-bar {{
      height: 9px;
      border-radius: 999px;
      background: #e6eaf0;
      overflow: hidden;
      margin-top: 10px;
    }}

    .confidence-bar i {{
      display: block;
      height: 100%;
      width: {confidence_pct}%;
      background: linear-gradient(90deg, #37b88f, var(--accent));
    }}

    .tabs {{
      display: flex;
      gap: 8px;
      margin: 0 0 18px;
      flex-wrap: wrap;
    }}

    .tab {{
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      padding: 9px 14px;
      color: var(--ink);
      font-weight: 700;
      cursor: pointer;
      transition: background 140ms ease, border-color 140ms ease, color 140ms ease;
    }}

    .tab[aria-selected="true"] {{
      background: var(--navy);
      color: #fff;
      border-color: var(--navy);
    }}

    .panel {{
      display: none;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel);
      padding: 22px 24px;
      min-height: 250px;
    }}

    .panel.is-active {{ display: block; }}

    .panel h2 {{
      margin: 0 0 14px;
      font-size: 22px;
    }}

    .panel p {{
      margin: 0 0 16px;
      color: #4f5968;
      font-size: 16px;
      line-height: 1.58;
    }}

    .bullet-list {{
      display: grid;
      gap: 12px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}

    .bullet-list li {{
      display: grid;
      grid-template-columns: 14px 1fr;
      gap: 12px;
      align-items: start;
      color: #4f5968;
      line-height: 1.45;
    }}

    .dot {{
      width: 11px;
      height: 11px;
      border-radius: 50%;
      margin-top: 5px;
      background: var(--accent);
    }}

    .dot.verification-pass {{ background: var(--green); }}
    .dot.verification-warn {{ background: #d6a80f; }}
    .dot.verification-block {{ background: #b3182c; }}

    .ranked-list,
    .trace-list,
    .source-list {{
      display: grid;
      gap: 12px;
      margin: 18px 0 0;
      padding: 0;
      list-style: none;
    }}

    .ranked-list li,
    .trace-list li,
    .source-list li {{
      display: grid;
      grid-template-columns: 34px 1fr;
      gap: 12px;
      align-items: start;
      border-top: 1px solid #edf0f5;
      padding-top: 12px;
    }}

    .rank,
    .step-index {{
      width: 30px;
      height: 30px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: var(--accent);
      color: #fff;
      font-weight: 800;
      font-size: 13px;
    }}

    .step-index {{
      background: var(--navy);
    }}

    .ranked-list strong,
    .trace-list strong,
    .source-list strong {{
      display: block;
      font-size: 15px;
      color: var(--ink);
      margin-bottom: 3px;
    }}

    .ranked-list small,
    .trace-list small,
    .source-list small {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
      margin-bottom: 4px;
    }}

    .ranked-list em,
    .trace-list em,
    .source-list em {{
      display: block;
      color: #4f5968;
      font-size: 13px;
      font-style: normal;
      line-height: 1.45;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      background: #f8fafc;
      border: 1px solid var(--line);
      padding: 8px 12px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      margin: 4px 6px 4px 0;
    }}

    .approval {{
      margin-top: 20px;
      border-radius: 14px;
      border: 1px solid #cfd8e5;
      background: #f8fafc;
      padding: 16px 18px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 18px;
      align-items: center;
    }}

    .approval strong {{
      display: block;
      margin-bottom: 4px;
    }}

    .switch {{
      border: 0;
      border-radius: 999px;
      width: 118px;
      height: 40px;
      background: #dbe3ee;
      color: #263044;
      font-weight: 800;
      cursor: pointer;
    }}

    .switch.is-approved {{
      background: #0f8f67;
      color: #fff;
    }}

    .footer-note {{
      margin-top: 20px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}

    @media (max-width: 900px) {{
      .report-shell {{
        grid-template-columns: 1fr;
        padding: 28px 22px;
      }}

      .body-card {{
        width: min(560px, 100%);
        height: 360px;
      }}

      .status-row {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="report-shell">
    <section class="figure-stage" aria-label="Interactive anatomical research figure">
      <div class="body-card">
        <img class="body-template" src="{body_template_uri}" alt="Clinical front and back human body reference diagram">
        {hotspot_markup}
      </div>
      <p class="caption">Interactive clinical body reference with an evidence-derived organ marker. Click the highlighted organ or report tabs to inspect evidence.</p>
    </section>

    <section class="content">
      <h1>GenomIQ Evidence Visualizer</h1>
      <p class="subtitle">Research-grade precision oncology evidence review. This demo is not a diagnosis tool and must not be used for treatment decisions.</p>

      <div class="status-row" aria-label="Report status">
        <div class="stat">
          <span>Research Signal</span>
          <strong>{escape(assessment.tier.value)}</strong>
        </div>
        <div class="stat">
          <span>Confidence</span>
          <strong>{confidence_pct}%</strong>
          <div class="confidence-bar" aria-hidden="true"><i></i></div>
        </div>
        <div class="stat">
          <span>Claim Status</span>
          <strong>{escape(assessment.claim_status.value)}</strong>
        </div>
      </div>

      <div class="tabs" role="tablist" aria-label="Report sections">
        <button class="tab" role="tab" aria-selected="true" data-panel="summary">Summary</button>
        <button class="tab" role="tab" aria-selected="false" data-panel="evidence">Evidence</button>
        <button class="tab" role="tab" aria-selected="false" data-panel="workiq">Work IQ</button>
        <button class="tab" role="tab" aria-selected="false" data-panel="reasoning">Reasoning</button>
        <button class="tab" role="tab" aria-selected="false" data-panel="safety">Safety</button>
      </div>

      <article class="panel is-active" id="summary" role="tabpanel">
        <h2>Research Summary</h2>
        <p>{escape(assessment.rationale)}</p>
        <span class="badge">Organ: {escape(assessment.organ)}</span>
        <span class="badge">Tier: {escape(assessment.tier.value)}</span>
        <span class="badge">HITL export required</span>
        {"".join(f'<span class="badge">Input: {escape(item)}</span>' for item in parsed_variants)}
        <ol class="ranked-list">
          {disease_rows}
        </ol>
      </article>

      <article class="panel" id="evidence" role="tabpanel">
        <h2>Evidence & Source Interpretation</h2>
        <p>Variant annotations and citation records are carried into the report from the MCP/NCBI/PubMed evidence path. Foundry IQ can replace or augment this source layer in approved environments.</p>
        <h3>Variant Annotation</h3>
        <ul class="source-list">
          {annotation_rows}
        </ul>
        <h3>Literature Evidence</h3>
        <ul class="source-list">
          {evidence_rows}
          <li><span class="dot"></span><span>Claims without citation coverage are blocked before export.</span></li>
        </ul>
      </article>

      <article class="panel" id="workiq" role="tabpanel">
        <h2>Work IQ Context</h2>
        <ul class="bullet-list">
          {"".join(f'<li><span class="dot" style="background: var(--green)"></span><span>{escape(item)}</span></li>' for item in context_ids)}
          <li><span class="dot" style="background: var(--green)"></span><span>Synthetic demo context only. No PHI, PII, secrets, or real workplace data.</span></li>
        </ul>
      </article>

      <article class="panel" id="reasoning" role="tabpanel">
        <h2>Multi-Agent Reasoning Trace</h2>
        <ol class="trace-list">
          {trace_rows}
        </ol>
      </article>

      <article class="panel" id="safety" role="tabpanel">
        <h2>Safety Gate</h2>
        <ul class="bullet-list">
          {"".join(f'<li><span class="dot"></span><span>{escape(item)}</span></li>' for item in blocked_reasons)}
          {verification_rows}
          <li><span class="dot"></span><span>Human reviewer approval is required before report export.</span></li>
          <li><span class="dot"></span><span>The visual diagram is illustrative and deterministic, not a clinical image interpretation.</span></li>
          {"".join(f'<li><span class="dot"></span><span>{escape(item)}</span></li>' for item in health_guidance)}
        </ul>
      </article>

      <div class="approval">
        <div>
          <strong>Human-in-the-loop export state</strong>
          <span id="approval-copy">Pending reviewer approval in production workflows.</span>
        </div>
        <button class="switch" id="approval-toggle" type="button" aria-pressed="false">Pending</button>
      </div>

      <p class="footer-note">Single-file HTML report. All styling, interaction logic, and the clinical-style diagram are embedded locally for hackathon demo portability.</p>
    </section>
    <div class="watermark">GenomIQ / Synthetic Demo</div>
  </main>

  <script>
    const report = {_js_json(report_payload)};
    const tabs = Array.from(document.querySelectorAll(".tab"));
    const panels = Array.from(document.querySelectorAll(".panel"));
    const organs = Array.from(document.querySelectorAll("[data-region='organ']"));
    const approvalButton = document.querySelector("#approval-toggle");
    const approvalCopy = document.querySelector("#approval-copy");

    function selectPanel(id) {{
      tabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.panel === id)));
      panels.forEach((panel) => panel.classList.toggle("is-active", panel.id === id));
    }}

    tabs.forEach((tab) => {{
      tab.addEventListener("click", () => selectPanel(tab.dataset.panel));
    }});

    organs.forEach((organ) => organ.addEventListener("click", () => {{
      organ.classList.toggle("is-active");
      selectPanel("summary");
    }}));

    approvalButton.addEventListener("click", () => {{
      const approved = approvalButton.getAttribute("aria-pressed") !== "true";
      approvalButton.setAttribute("aria-pressed", String(approved));
      approvalButton.classList.toggle("is-approved", approved);
      approvalButton.textContent = approved ? "Approved" : "Pending";
      approvalCopy.textContent = approved
        ? "Demo approval toggled locally. Production export still requires a qualified reviewer."
        : "Pending reviewer approval in production workflows.";
    }});

    window.genomiqReport = report;
  </script>
</body>
</html>
"""

    html_path.write_text(html, encoding="utf-8")
    json_path.write_text(json.dumps(assessment.to_dict(), indent=2), encoding="utf-8")

    return VisualReport(
        title="GenomIQ Evidence Visualizer Report",
        assessment=assessment,
        html_path=str(html_path),
        json_path=str(json_path),
    )
