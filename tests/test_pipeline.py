import tempfile
import sys
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from genomiq.evidence import DemoFoundryIQEvidenceRetriever
from genomiq.mcp_tools import VariantAnnotationMCPTool
from genomiq.parser import parse_research_case
from genomiq.risk import assess_research_risk
from genomiq.schema import ClaimStatus, RiskTier
from genomiq.visualizer import write_visual_report
from genomiq.work_context import DemoWorkIQContextRetriever
from api_server import build_openapi, generate_report


MCP_SERVER_PATH = Path(__file__).resolve().parents[1] / "mcp_servers" / "genomiq_variant_server.py"
MCP_SERVER_SPEC = spec_from_file_location("genomiq_variant_server", MCP_SERVER_PATH)
assert MCP_SERVER_SPEC is not None
genomiq_variant_server = module_from_spec(MCP_SERVER_SPEC)
assert MCP_SERVER_SPEC.loader is not None
MCP_SERVER_SPEC.loader.exec_module(genomiq_variant_server)

RAG_BUILDER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_ncbi_rag_dataset.py"
RAG_BUILDER_SPEC = spec_from_file_location("build_ncbi_rag_dataset", RAG_BUILDER_PATH)
assert RAG_BUILDER_SPEC is not None
build_ncbi_rag_dataset = module_from_spec(RAG_BUILDER_SPEC)
assert RAG_BUILDER_SPEC.loader is not None
sys.modules["build_ncbi_rag_dataset"] = build_ncbi_rag_dataset
RAG_BUILDER_SPEC.loader.exec_module(build_ncbi_rag_dataset)


class PipelineTests(unittest.TestCase):
    def test_brca_parp_demo_signal_is_supported(self) -> None:
        parsed = parse_research_case("Synthetic de-identified ovarian case with BRCA1 and PARP pathway dependency.")
        evidence = DemoFoundryIQEvidenceRetriever().retrieve(parsed)
        context = DemoWorkIQContextRetriever().retrieve(parsed)
        assessment = assess_research_risk(parsed, evidence, context)

        self.assertEqual(assessment.tier, RiskTier.HIGH)
        self.assertEqual(assessment.claim_status, ClaimStatus.SUPPORTED)
        self.assertEqual(assessment.evidence_ids, ["PMCID:DEMO-BRCA-PARP-001"])

    def test_sensitive_identifier_blocks_export(self) -> None:
        parsed = parse_research_case("Synthetic BRCA1 PARP case. MRN: ABC-123")
        evidence = DemoFoundryIQEvidenceRetriever().retrieve(parsed)
        context = DemoWorkIQContextRetriever().retrieve(parsed)
        assessment = assess_research_risk(parsed, evidence, context)

        self.assertEqual(assessment.claim_status, ClaimStatus.BLOCKED)
        self.assertTrue(assessment.blocked_reasons)

    def test_coordinate_marker_is_parsed_and_annotated_without_network(self) -> None:
        parsed = parse_research_case("Synthetic variant coordinate chr7:182734 for source interpretation.")
        self.assertIn("chr7:182734", parsed.variants)

        annotation = VariantAnnotationMCPTool().annotate("chr7:182734")
        self.assertEqual(annotation.chromosome, "7")
        self.assertEqual(annotation.dbsnp_id, "requires_live_ncbi_lookup")

    def test_vcf_row_is_parsed_as_coordinate_marker(self) -> None:
        parsed = parse_research_case(
            "\n".join(
                [
                    "Synthetic de-identified VCF snippet.",
                    "#CHROM POS ID REF ALT QUAL FILTER INFO",
                    "7 182734 . A G 100 PASS .",
                ]
            )
        )

        self.assertIn("chr7:182734:A>G", parsed.variants)
        annotation = VariantAnnotationMCPTool().annotate("chr7:182734:A>G")
        self.assertEqual(annotation.coordinate, "7:182734")
        self.assertEqual(annotation.reference, "A")
        self.assertEqual(annotation.alternate, "G")

    def test_braf_v600e_colorectal_case_is_supported(self) -> None:
        parsed = parse_research_case(
            "Synthetic colorectal cancer research case with BRAF_V600E and chr7:g.140753336A>T."
        )
        self.assertEqual(parsed.primary_research_area, "Colorectal cancer research")
        self.assertIn("BRAF_V600E", parsed.variants)
        self.assertIn("chr7:140753336:A>T", parsed.variants)

        annotation = VariantAnnotationMCPTool().annotate("BRAF_V600E")
        self.assertEqual(annotation.gene_name, "BRAF")
        self.assertEqual(annotation.dbsnp_id, "rs113488022")

        evidence = DemoFoundryIQEvidenceRetriever().retrieve(parsed)
        context = DemoWorkIQContextRetriever().retrieve(parsed)
        assessment = assess_research_risk(parsed, evidence, context)
        self.assertEqual(assessment.claim_status, ClaimStatus.SUPPORTED)

    def test_mcp_server_lists_and_calls_variant_tool(self) -> None:
        list_response = genomiq_variant_server.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        )
        self.assertEqual(list_response["result"]["tools"][0]["name"], "annotate_variant")

        call_response = genomiq_variant_server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "annotate_variant",
                    "arguments": {"variant": "chr7:182734:A>G"},
                },
            }
        )

        structured = call_response["result"]["structuredContent"]
        self.assertEqual(structured["chromosome"], "7")
        self.assertEqual(structured["reference"], "A")
        self.assertEqual(structured["alternate"], "G")

    def test_openapi_wrapper_generates_report_payload(self) -> None:
        spec = build_openapi("http://localhost:8000")
        self.assertIn("/generate-report", spec["paths"])

        status, response = generate_report(
            {
                "case_text": "Synthetic de-identified ovarian case with BRCA1 and PARP.",
                "approved_for_export": True,
            },
            "http://localhost:8000",
        )

        self.assertEqual(status, 200)
        self.assertEqual(response["status"], "report_generated")
        self.assertIn("BRCA1_mut", response["parsed_variants"])
        self.assertIn("/reports/genomiq_interactive_report.html?v=", response["report_url"])

    def test_visual_report_writes_html_and_json(self) -> None:
        parsed = parse_research_case("Synthetic de-identified ovarian case with BRCA1 and PARP.")
        assessment = assess_research_risk(
            parsed,
            DemoFoundryIQEvidenceRetriever().retrieve(parsed),
            DemoWorkIQContextRetriever().retrieve(parsed),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            report = write_visual_report(assessment, Path(temp_dir))

            self.assertTrue(Path(report.html_path).exists())
            self.assertTrue(Path(report.json_path).exists())
            self.assertIn("GenomIQ Evidence Visualizer", Path(report.html_path).read_text(encoding="utf-8"))

    def test_ncbi_rag_dataset_builder_offline_mode(self) -> None:
        seed_path = Path(__file__).resolve().parents[1] / "knowledge" / "variant_seed_queries.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "ncbi_variant_rag_dataset.md"
            markdown = build_ncbi_rag_dataset.build_dataset(seed_path, output_path, retmax=1, offline=True)

            self.assertTrue(output_path.exists())
            self.assertIn("GenomIQ NCBI Variant Evidence RAG Dataset", markdown)
            self.assertIn("BRAF_V600E", markdown)
            self.assertIn("KRAS_G12D", markdown)


if __name__ == "__main__":
    unittest.main()
