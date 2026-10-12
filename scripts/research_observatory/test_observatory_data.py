import tempfile
import unittest
import json
import hashlib
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

import observatory_data
from observatory_data import SOURCE_FAMILIES, load_observatory, read_allowed_preview


class ObservatoryDataTests(unittest.TestCase):
    def test_source_summaries_are_specific_to_their_verified_content(self):
        files = {
            "docs/ARTICLE.md": b"# Do Large Language Models Rediscover TRIZ?\n",
            "docs/LAB03.md": b"---\ntitle: Lab 03 behavioral baseline contract\n"
            b"description: Public contract for fail-closed behavioral baselines.\n---\n",
        }
        records = observatory_data._build_source_records(files, paths=files)
        by_path = {record["path"]: record for record in records}
        self.assertIn("hypothes", by_path["docs/ARTICLE.md"]["summary"].lower())
        self.assertIn("behavioral baselines", by_path["docs/LAB03.md"]["summary"].lower())
        self.assertEqual(
            by_path["docs/LAB03.md"]["summary"],
            "Public contract for fail-closed behavioral baselines.",
        )
        self.assertNotEqual(by_path["docs/ARTICLE.md"]["summary"], by_path["docs/LAB03.md"]["summary"])
        self.assertEqual(
            by_path["docs/LAB03.md"]["sha256"], hashlib.sha256(files["docs/LAB03.md"]).hexdigest()
        )

    def test_result_summary_does_not_invent_outcome_for_missing_file(self):
        path = "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/report.md"
        records = observatory_data._build_source_records({path: None}, paths=[path])
        self.assertIn("missing", records[0]["summary"].lower())
        self.assertNotIn("null", records[0]["summary"].lower())

    def test_exp002_manifest_summary_reads_nested_terminal_status(self):
        path = ("results/exp002/qwen-qwen3-0-6b-base/"
                "exp002-qwen3-0-6b-exp002a-20260820-01/publication-manifest.json")
        payload = json.dumps({"status": "published", "packages": [
            {"model_id": "Qwen/Qwen3-0.6B-Base", "terminal_status": "null"}
        ]}).encode()
        record = observatory_data._build_source_records({path: payload}, paths=[path])[0]
        self.assertIn("Qwen3-0.6B-Base", record["summary"])
        self.assertIn("terminal status: null", record["summary"])
        self.assertNotIn("not stated", record["summary"])

    def test_a0_reports_name_only_their_own_recorded_outcome(self):
        examples = {
            "results/a0/a0-v1.0.3-e93a9faa/report.html":
                b"<p><strong>Final status:</strong> positive</p>",
            "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/report.md":
                b"- Result status: positive\n",
            "results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/report.md":
                b"- Terminal status: `positive`\n",
        }
        by_path = {record["path"]: record for record in
                   observatory_data._build_source_records(examples, paths=examples)}
        for path, record in by_path.items():
            with self.subTest(path=path):
                self.assertIn("recorded outcome: positive", record["summary"])
                self.assertIn("exploratory", record["summary"].lower())
        self.assertIn("analysis-only", by_path[next(path for path in examples if "a0r2c3" in path)]["summary"])

    def test_a0_manifest_does_not_confuse_status_with_publication_or_outcome(self):
        path = "results/a0/a0-v1.0.3-e93a9faa/publication-manifest.json"
        record = observatory_data._build_source_records(
            {path: b'{"status":"pass","scientific_status":"exploratory"}'}, paths=[path]
        )[0]
        self.assertIn("recorded manifest status: pass", record["summary"])
        self.assertNotIn("recorded outcome: pass", record["summary"])
        c3_path = ("results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/"
                   "publication-manifest.json")
        c3 = observatory_data._build_source_records(
            {c3_path: b'{"status":"positive","terminal_status":"positive"}'},
            paths=[c3_path],
        )[0]
        self.assertIn("recorded manifest status: positive", c3["summary"])
        self.assertNotIn("publication status", c3["summary"])

    def test_public_source_synopses_cover_all_66_hash_bound_files(self):
        root = Path(__file__).resolve().parents[2]
        data = load_observatory(root, strict_public=True)
        self.assertEqual(len(data["sources"]), 66)
        self.assertTrue(all(source["sha256"] and source["summary"] for source in data["sources"]))
        self.assertFalse(any("Allowlisted research source" in source["summary"]
                             for source in data["sources"]))
        qwen = next(source for source in data["sources"]
                    if source["path"].endswith("exp002-qwen3-0-6b-exp002a-20260820-01/publication-manifest.json"))
        self.assertIn("terminal status: null", qwen["summary"])

    def test_repository_root_is_validated_from_packaged_app_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            app_file = root / "scripts/research_observatory/app.py"
            self._write(root, "scripts/research_observatory/app.py", "# app\n")
            self._write(root, "pyproject.toml", "[project]\nname = 'latent-triz'\n")
            self._write(root, "docs/ARTICLE.md", "Public article\n")
            resolver = getattr(observatory_data, "resolve_repository_root", None)
            self.assertTrue(callable(resolver), "packaged app root resolver is missing")
            self.assertEqual(resolver(app_file), root)
            (root / "docs/ARTICLE.md").unlink()
            with self.assertRaises(ValueError):
                resolver(app_file)

    def test_source_reader_rejects_oversized_and_hardlinked_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._write(root, "docs/ARTICLE.md", "x" * (2 * 1024 * 1024 + 1))
            with self.assertRaises(PermissionError):
                load_observatory(root)
            self._write(root, "docs/ARTICLE.md", "small\n")
            (root / "alias").hardlink_to(root / "docs/ARTICLE.md")
            with self.assertRaises(PermissionError):
                load_observatory(root)

    def test_reader_limits_bytes_even_if_size_metadata_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._write(root, "docs/ARTICLE.md", "x" * (2 * 1024 * 1024 + 1))
            real_fstat = observatory_data.os.fstat
            def stale_size(fd):
                actual = real_fstat(fd)
                return SimpleNamespace(st_mode=actual.st_mode, st_nlink=actual.st_nlink, st_size=1)
            with mock.patch.object(observatory_data.os, "fstat", side_effect=stale_size):
                with self.assertRaises(PermissionError):
                    observatory_data._read_allowlisted(root, "docs/ARTICLE.md")

    def test_public_mode_rejects_sources_without_clean_git_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._write(root, "docs/ARTICLE.md", "local only\n")
            try:
                with self.assertRaises(PermissionError):
                    load_observatory(root, strict_public=True)
            except TypeError:
                self.fail("public mode must enforce clean Git provenance before reading")

    def test_public_source_inventory_rejects_unapproved_hash(self):
        validator = getattr(observatory_data, "validate_source_inventory", None)
        self.assertTrue(callable(validator), "public source-inventory validator is missing")
        records = [{"path": "docs/ARTICLE.md", "family": "selected_docs", "sha256": "a" * 64}]
        manifest = {"schema": "research-observatory-source-inventory-v1", "entries": [
            {"path": "docs/ARTICLE.md", "family": "selected_docs", "sha256": "a" * 64}
        ]}
        validator(records, manifest)
        records[0]["sha256"] = "b" * 64
        with self.assertRaises(PermissionError):
            validator(records, manifest)

    def test_higher_claim_levels_are_not_inferred_without_canonical_validation(self):
        candidate = self._claim(evidence_level="E1", status="preliminary", non_empirical=False)
        self.assertFalse(observatory_data._valid_claim(candidate))

    def test_inventory_reader_rejects_symlink_before_open(self):
        reader = getattr(observatory_data, "read_source_inventory", None)
        self.assertTrue(callable(reader), "safe inventory reader is missing")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            target = root / "inventory.json"
            target.write_text('{"schema":"research-observatory-source-inventory-v1","entries":[]}', encoding="utf-8")
            alias = root / "alias.json"
            alias.symlink_to(target)
            self.assertEqual(reader(target)["entries"], [])
            with self.assertRaises(PermissionError):
                reader(alias)

    def test_catalogue_has_independently_counted_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = load_observatory(Path(tmp).resolve())

        counts = {}
        for source in data["sources"]:
            counts[source["family"]] = counts.get(source["family"], 0) + 1
        self.assertEqual(
            counts,
            {
                "selected_docs": 22,
                "navigation_snapshot": 3,
                "formal_claims": 2,
                "triz_reference": 2,
                "study_protocol": 3,
                "a0": 2,
                "a0_r1": 2,
                "a0_r2_c3": 2,
                "exp001_comparative": 14,
                "exp002_baseline": 14,
            },
        )
        self.assertEqual(len(data["observations"]), 35)
        statuses = {item["status"] for item in data["observations"]}
        self.assertEqual(statuses, {"not_inspected", "not_interpretable"})
        self.assertEqual(
            sum(item["status"] == "not_interpretable" for item in data["observations"]), 3
        )
        missing_manifest = next(
            item for item in data["sources"]
            if item["path"] == "results/a0/a0-v1.0.3-e93a9faa/publication-manifest.json"
        )
        self.assertEqual(missing_manifest["freshness"], "missing")
        self.assertTrue(missing_manifest["conflict_markers"])

    def test_stale_navigation_sources_are_visible_as_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._write(root, "docs/CURRENT_STATUS.md", "# Historical status\n")
            self._write(root, "results/README.md", "# Historical index\n")
            data = load_observatory(root)
        self.assertTrue(any("docs/CURRENT_STATUS.md" in warning for warning in data["warnings"]))
        self.assertTrue(any("results/README.md" in warning for warning in data["warnings"]))

    def test_decision_categories_are_curated_by_adr_not_body_keywords(self):
        self.assertEqual(
            observatory_data._decision_category(
                "docs/decisions/0003-exp-001-model-selection.md", "publication execution"
            ),
            "scientific design",
        )
        self.assertEqual(
            observatory_data._decision_category(
                "docs/decisions/0009-lab05-candidate-directions.md", "publication execution"
            ),
            "scientific design",
        )

    def test_c3_positive_is_analysis_recovery_not_new_proxy_signal(self):
        status = observatory_data._map_summary_status(
            "positive", {"evidence_eligible": False, "scientific_status": "exploratory"},
            [], "A0-R2-C3",
        )
        self.assertEqual(status, "analysis_only_recovery")

    def test_claims_and_experiment_statuses_are_source_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._write(
                root,
                "data/claims.jsonl",
                '{"claim_id":"CLM-001","statement":"Example claim",'
                '"principle":"Example","track":"pretrained",'
                '"model_scope":{"name":"unselected","family":"to be verified",'
                '"revision":"unselected"},"status":"untested",'
                '"evidence_level":"E0","falsification_condition":"Example",'
                '"preregistrations":[],"dataset_snapshots":[],"experiments":[],"results":[],"replications":[],"non_empirical":true,'
                '"evidence_profile":{"behavioral_effect":false,"lexical_controls":false,"cross_domain":false,"decodable":false,"positive_causal_intervention":false,"negative_causal_intervention":false,"dose_response":false,"capability_preserved":false,"independent_replication":false,"cross_model_replication":false,"controlled_training":false},'
                '"last_verified":"2026-08-13"}\n',
            )
            manifest = (
                "results/exp001-comparative/"
                "smollm2-135m-93efa2f0-smollm2-135m-20260819-01/publication-manifest.json"
            )
            report = manifest.rsplit("/", 1)[0] + "/report.md"
            report_text = "Terminal status: null\n"
            self._write(root, report, report_text)
            self._write(
                root,
                manifest,
                json.dumps({
                    "model_id": "HuggingFaceTB/SmolLM2-135M",
                    "terminal_status": "null",
                    "evidence_eligible": False,
                    "report": {"path": report, "sha256": hashlib.sha256(report_text.encode()).hexdigest()},
                }),
            )
            data = load_observatory(root)

        claim = data["claims"][0]
        self.assertEqual((claim["claim_id"], claim["status"], claim["evidence_level"]),
                         ("CLM-001", "untested", "E0"))
        self.assertEqual(claim["source"], "data/claims.jsonl")
        observation = next(
            item for item in data["observations"]
            if item["model"] == "HuggingFaceTB/SmolLM2-135M"
            and item["campaign"] == "EXP-001 comparative"
        )
        self.assertEqual(observation["status"], "null")
        self.assertIn("publication-manifest.json", observation["source"])
        self.assertEqual(observation["metric"], None)

    def test_unknown_status_fails_closed_and_preview_rejects_non_allowlisted_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            allowed = (
                "results/exp001-comparative/"
                "smollm2-135m-93efa2f0-smollm2-135m-20260819-01/"
                "publication-manifest.json"
            )
            report = allowed.rsplit("/", 1)[0] + "/report.md"
            report_text = "Terminal status: surprise\n"
            self._write(root, report, report_text)
            self._write(
                root,
                allowed,
                json.dumps({
                    "model_id": "HuggingFaceTB/SmolLM2-135M",
                    "terminal_status": "surprise",
                    "evidence_eligible": False,
                    "report": {"path": report, "sha256": hashlib.sha256(report_text.encode()).hexdigest()},
                }),
            )
            self._write(root, "outside.txt", "must not be included")
            data = load_observatory(root)
            observation = next(
                item for item in data["observations"]
                if item["model"] == "HuggingFaceTB/SmolLM2-135M"
                and item["campaign"] == "EXP-001 comparative"
            )
            self.assertEqual(observation["status"], "not_interpretable")
            self.assertTrue(data["warnings"])
            with self.assertRaises(PermissionError):
                read_allowed_preview(root, "outside.txt")
            with self.assertRaises(PermissionError):
                read_allowed_preview(
                    root,
                    "results/a0/a0-v1.0.3-e93a9faa/statistical-result.json",
                )
            for forbidden in (
                "response-index.json", "sealed-result.json", "sealed-targets",
                "private-map", "raw-response", ".a0x-runtime",
            ):
                self.assertFalse(any(forbidden in path for path in SOURCE_FAMILIES))

    def test_unadmitted_result_is_excluded_before_reading_or_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            report_text = "Terminal status: auto_proxy_signal\n"
            self._write(
                root,
                "results/not-admitted/publication-manifest.json",
                json.dumps({
                    "artifact_class": "synthetic-unadmitted-manifest",
                    "model_terminal_map": {"HuggingFaceTB/SmolLM2-135M": {"UNPUBLISHED": "auto_proxy_signal"}},
                    "report": {"path": "report.md", "sha256": hashlib.sha256(report_text.encode()).hexdigest()},
                }),
            )
            self._write(
                root,
                "results/not-admitted/report.md",
                report_text,
            )
            data = load_observatory(root)
            self.assertNotIn("UNPUBLISHED", data["campaign_names"])
            self.assertFalse(any(source["path"].startswith("results/not-admitted/") for source in data["sources"]))
            with self.assertRaises(PermissionError):
                read_allowed_preview(root, "results/not-admitted/report.md")

    def test_preview_rejects_content_changed_after_catalogue_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._write(root, "docs/ARTICLE.md", "approved snapshot\n")
            data = load_observatory(root)
            source = next(item for item in data["sources"] if item["path"] == "docs/ARTICLE.md")
            self._write(root, "docs/ARTICLE.md", "changed after snapshot\n")
            try:
                with self.assertRaises(PermissionError):
                    read_allowed_preview(root, "docs/ARTICLE.md", expected_sha256=source["sha256"])
            except TypeError:
                self.fail("preview must accept and enforce the snapshot SHA-256")

    def test_snapshot_identity_changes_with_source_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._write(root, "docs/ARTICLE.md", "first public text\n")
            first = load_observatory(root)
            self._write(root, "docs/ARTICLE.md", "second public text\n")
            second = load_observatory(root)
        self.assertIn("snapshot_sha256", first)
        self.assertRegex(first["snapshot_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(first["snapshot_sha256"], second["snapshot_sha256"])

    def test_c3_protocol_hash_mismatch_fails_closed_for_only_its_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._write(
                root,
                "experiments/a0r2-independent-model/study-protocol.json",
                '{"protocol_id":"a0r2-independent-model-v1.0.0",'
                '"protocol_status":"frozen","scientific_status":"exploratory",'
                '"evidence_eligible":false,"model":{"id":"HuggingFaceTB/SmolLM2-360M",'
                '"revision":"f8027fd0"}}',
            )
            self._write(
                root,
                "results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/publication-manifest.json",
                '{"protocol":{"path":"experiments/a0r2-independent-model/study-protocol.json",'
                '"sha256":"' + "0" * 64 + '"},"evidence_eligible":false}',
            )
            self._write(
                root,
                "results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/report.md",
                "Terminal status: positive\n",
            )
            data = load_observatory(root)
        c3 = next(
            item for item in data["observations"]
            if item["campaign"] == "A0-R2-C3"
            and item["model"] == "HuggingFaceTB/SmolLM2-360M"
        )
        other = next(
            item for item in data["observations"]
            if item["campaign"] == "A0-R2-C3"
            and item["model"] == "EleutherAI/pythia-70m-deduped"
        )
        self.assertEqual(c3["status"], "not_interpretable")
        self.assertEqual(other["status"], "not_inspected")

    def test_manifest_report_hash_conflict_invalidates_only_bound_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = (
                "results/exp001-comparative/"
                "smollm2-135m-93efa2f0-smollm2-135m-20260819-01/"
                "publication-manifest.json"
            )
            report = manifest.rsplit("/", 1)[0] + "/report.md"
            self._write(
                root,
                report,
                "Terminal status: null\n",
            )
            self._write(
                root,
                manifest,
                '{"model_id":"HuggingFaceTB/SmolLM2-135M",'
                '"terminal_status":"null","evidence_eligible":false,'
                '"report":{"path":"' + report + '","sha256":"' + "0" * 64 + '"}}',
            )
            data = load_observatory(root)
        observation = next(
            item for item in data["observations"]
            if item["model"] == "HuggingFaceTB/SmolLM2-135M"
            and item["campaign"] == "EXP-001 comparative"
        )
        source = next(item for item in data["sources"] if item["path"] == report)
        self.assertEqual(observation["status"], "not_interpretable")
        self.assertEqual(source["freshness"], "hash_mismatch")

    def test_malformed_types_and_unbound_report_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._write(
                root,
                "data/claims.jsonl",
                json.dumps(self._claim(track=[])) + "\n",
            )
            manifest = (
                "results/exp001-comparative/"
                "smollm2-135m-93efa2f0-smollm2-135m-20260819-01/"
                "publication-manifest.json"
            )
            report = manifest.rsplit("/", 1)[0] + "/report.md"
            report_text = "Terminal status: null\n"
            self._write(root, report, report_text)
            self._write(
                root,
                manifest,
                json.dumps({
                    "model_id": "HuggingFaceTB/SmolLM2-135M",
                    "terminal_status": [],
                    "evidence_eligible": False,
                    "report": {"path": report, "sha256": hashlib.sha256(report_text.encode()).hexdigest()},
                }),
            )
            second_manifest = (
                "results/exp001-comparative/gpt2-607a30d7-gpt2-20260819-01/"
                "publication-manifest.json"
            )
            second_report = second_manifest.rsplit("/", 1)[0] + "/report.md"
            second_report_text = "Terminal status: positive\n"
            self._write(root, second_report, second_report_text)
            self._write(
                root,
                second_manifest,
                json.dumps({
                    "model_id": "openai-community/gpt2",
                    "terminal_status": "positive",
                    "scientific_status": [],
                    "evidence_eligible": False,
                    "report": {"path": second_report, "sha256": hashlib.sha256(second_report_text.encode()).hexdigest()},
                }),
            )
            data = load_observatory(root)
        claim = data["claims"][0]
        observation = next(
            item for item in data["observations"]
            if item["model"] == "HuggingFaceTB/SmolLM2-135M"
            and item["campaign"] == "EXP-001 comparative"
        )
        positive_observation = next(
            item for item in data["observations"]
            if item["model"] == "openai-community/gpt2"
            and item["campaign"] == "EXP-001 comparative"
        )
        self.assertEqual(claim["status"], "not_interpretable")
        self.assertEqual(observation["status"], "not_interpretable")
        self.assertEqual(positive_observation["status"], "not_interpretable")

    def test_manifest_cannot_bind_another_packages_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = (
                "results/exp001-comparative/"
                "smollm2-135m-93efa2f0-smollm2-135m-20260819-01/publication-manifest.json"
            )
            wrong_report = (
                "results/exp001-comparative/gpt2-607a30d7-gpt2-20260819-01/report.md"
            )
            wrong_text = "Terminal status: null\n"
            self._write(root, wrong_report, wrong_text)
            self._write(
                root,
                manifest,
                json.dumps({
                    "model_id": "HuggingFaceTB/SmolLM2-135M",
                    "terminal_status": "null",
                    "evidence_eligible": False,
                    "report": {"path": wrong_report, "sha256": hashlib.sha256(wrong_text.encode()).hexdigest()},
                }),
            )
            data = load_observatory(root)
        observation = next(
            item for item in data["observations"]
            if item["model"] == "HuggingFaceTB/SmolLM2-135M"
            and item["campaign"] == "EXP-001 comparative"
        )
        manifest_source = next(item for item in data["sources"] if item["path"] == manifest)
        self.assertEqual(observation["status"], "not_interpretable")
        self.assertEqual(manifest_source["freshness"], "hash_mismatch")

    def test_preview_rejects_root_and_component_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as elsewhere:
            outside = Path(elsewhere).resolve()
            self._write(outside, "docs/ARTICLE.md", "outside")
            linked_root = Path(tmp).resolve() / "root-link"
            linked_root.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(PermissionError):
                read_allowed_preview(linked_root, "docs/ARTICLE.md")

            root = Path(tmp).resolve() / "checkout"
            root.mkdir()
            (root / "docs").symlink_to(outside / "docs", target_is_directory=True)
            with self.assertRaises(PermissionError):
                read_allowed_preview(root, "docs/ARTICLE.md")

    def test_preview_is_bounded_and_catalogue_sources_are_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            path = "docs/ARTICLE.md"
            self._write(root, path, "# Article\n" + "x" * 100)
            excerpt = read_allowed_preview(root, path, max_chars=24)
            source = next(item for item in load_observatory(root)["sources"]
                          if item["path"] == path)

        self.assertEqual(len(excerpt), 24)
        self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(source["freshness"], "local_snapshot")

    @staticmethod
    def _write(root, relative, text):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    @staticmethod
    def _claim(**overrides):
        entry = {
            "claim_id": "CLM-001",
            "statement": "Example claim",
            "principle": "Example",
            "track": "pretrained",
            "model_scope": {"name": "unselected", "family": "to be verified", "revision": "unselected"},
            "status": "untested",
            "evidence_level": "E0",
            "falsification_condition": "Example",
            "preregistrations": [],
            "dataset_snapshots": [],
            "experiments": [],
            "results": [],
            "replications": [],
            "non_empirical": True,
            "evidence_profile": {
                "behavioral_effect": False, "lexical_controls": False, "cross_domain": False,
                "decodable": False, "positive_causal_intervention": False,
                "negative_causal_intervention": False, "dose_response": False,
                "capability_preserved": False, "independent_replication": False,
                "cross_model_replication": False, "controlled_training": False,
            },
            "last_verified": "2026-08-13",
        }
        entry.update(overrides)
        return entry


if __name__ == "__main__":
    unittest.main()
