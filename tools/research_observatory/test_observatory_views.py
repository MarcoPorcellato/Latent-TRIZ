"""Focused tests for the observatory's presentation and epistemic boundaries."""

import unittest

import observatory_views as views


class ObservatoryViewTests(unittest.TestCase):
    def test_guided_tour_names_the_actual_source_preview_control(self):
        output = views.guided_questions_html()
        self.assertIn("Preview one allowlisted source", output)
        self.assertNotIn("open the cited", output)

    def test_source_derived_text_cannot_become_html_or_remote_embed(self):
        hostile = '<img src="https://example.invalid/x" onerror="alert(1)">'
        output = views.source_preview_html("docs/public.md", hostile)
        self.assertIn("&lt;img", output)
        self.assertNotIn(hostile, output)
        record = {
            "model": hostile, "campaign": "EXP-001 comparative", "status": "null",
            "scope": hostile, "notes": hostile, "source_paths": ["results/report.md"],
        }
        detail = views.matrix_detail_html(record)
        self.assertNotIn(hostile, detail)
        self.assertIn("&lt;img", detail)

    def test_missing_cell_is_not_a_null_result(self):
        rows = views.matrix_rows(
            [{"model": "M1", "campaign": "C1", "status": "null"}],
            ["M1", "M2"], ["C1"],
        )
        self.assertEqual(rows[0]["C1"], "Null")
        self.assertEqual(rows[1]["C1"], "Not inspected")

    def test_status_filter_never_relabels_known_result_as_uninspected(self):
        try:
            rows = views.matrix_rows(
                [
                    {"model": "M1", "campaign": "C1", "status": "positive_exploratory_proxy"},
                    {"model": "M2", "campaign": "C1", "status": "null"},
                    {"model": "M3", "campaign": "C1", "status": "not_inspected"},
                ],
                ["M1", "M2", "M3"], ["C1"], status_filter="null",
            )
        except TypeError:
            self.fail("matrix must distinguish filtered records from uninspected cells")
        self.assertEqual(rows[0]["C1"], "Filtered out")
        self.assertEqual(rows[1]["C1"], "Null")
        self.assertEqual(rows[2]["C1"], "Not inspected")

    def test_study_chart_excludes_other_campaigns(self):
        records = [
            {"model": "M1", "campaign": "C1", "status": "null"},
            {"model": "M2", "campaign": "C2", "status": "positive_exploratory_proxy"},
        ]
        output = views.categorical_bar_svg(records, "C1")
        self.assertIn("Null", output)
        self.assertNotIn("Exploratory proxy +", output)
        self.assertIn("1 visible records", output)

    def test_result_source_picker_contains_only_cited_allowlisted_study_sources(self):
        records = [
            {"campaign": "C1", "source_paths": ["docs/A.md", "private/secret.json"]},
            {"campaign": "C2", "source_paths": ["docs/B.md"]},
        ]
        picker = getattr(views, "result_source_paths", None)
        self.assertTrue(callable(picker), "study source picker is missing")
        self.assertEqual(picker(records, "C1", {"docs/A.md", "docs/B.md"}), ["docs/A.md"])

    def test_results_header_does_not_call_gaps_executed_models(self):
        records = [
            {"campaign": "A0", "status": "positive_exploratory_proxy"},
            {"campaign": "A0", "status": "not_inspected"},
        ]
        output = views.results_header_html("A0", records)
        self.assertIn("2 model cells, 1 with an inspected status", output)
        self.assertIn("including missing coverage", output)

    def test_overview_separates_c3_recovery_from_model_proxy_signals(self):
        records = [
            {"campaign": "A0", "status": "positive_exploratory_proxy"},
            {"campaign": "A0-R1", "status": "positive_exploratory_proxy"},
            {"campaign": "A0-R2-C3", "status": "analysis_only_recovery"},
        ]
        output = views.overview_html({"claims": [], "observations": records})
        self.assertIn("2</strong><span>exploratory proxy cells", output)
        self.assertIn("1</strong><span>analysis-only recovery cells", output)

    def test_route_does_not_promote_formal_claims(self):
        claims = [
            {"claim_id": "CLM-001", "evidence_level": "E0"},
            {"claim_id": "CLM-002", "evidence_level": "E0"},
        ]
        output = views.route_html("Causality", claims)
        self.assertIn("2 of 2 registered claims remain E0", output)
        self.assertIn("E6", output)
        self.assertIn("this local catalogue contains no", output)

    def test_route_places_causal_gate_before_composition_and_names_expert_validation(self):
        output = views.route_html("Causality", [])
        self.assertLess(output.index("Causality"), output.index("Compositionality"))
        self.assertIn("expert", output.lower())

    def test_snapshot_banner_identifies_local_commit_without_claiming_publication(self):
        snapshot = {
            "source_head": "a" * 40,
            "source_tree": "b" * 40,
            "snapshot_sha256": "c" * 64,
        }
        try:
            output = views.snapshot_banner_html(snapshot)
        except AttributeError:
            self.fail("snapshot provenance banner is missing")
        self.assertIn("aaaaaaaaaaaa", output)
        self.assertIn("cccccccccccc", output)
        self.assertIn("public publication is not verified", output.lower())

    def test_untracked_source_is_visibly_not_publication_proof(self):
        record = {
            "model": "M1", "campaign": "synthetic unpublished", "status": "auto_proxy_signal",
            "scope": "one package", "notes": "local observation",
            "source_paths": ["results/synthetic/report.md"],
        }
        sources = [{"path": "results/synthetic/report.md", "vcs_state": "untracked",
                    "source_scope": "local_untracked"}]
        detail = views.matrix_detail_html(record, sources)
        cards = views.result_cards_html([record], sources)
        for output in (detail, cards):
            self.assertIn("public publication is unverified", output)

    def test_overview_does_not_invent_missing_proxy_evidence(self):
        data = {"claims": [], "observations": [{"campaign": "EXP-001 comparative", "status": "null"}]}
        output = views.overview_html(data)
        self.assertIn("Early proxy-package status is incomplete", output)
        self.assertNotIn("A0 and A0-R1 report positive", output)

    def test_overview_does_not_call_model_packages_independent_replications(self):
        data = {"claims": [], "observations": [
            {"campaign": "EXP-001 comparative", "status": "null"}
        ]}
        output = views.overview_html(data)
        self.assertIn("separate model packages", output)
        self.assertNotIn("independent EXP-001 comparative results", output)


if __name__ == "__main__":
    unittest.main()
