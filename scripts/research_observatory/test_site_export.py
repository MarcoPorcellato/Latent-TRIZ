from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.research_observatory import observatory_data, site_export
from scripts.research_observatory.observatory_views import STATUS_LABELS


class SiteExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.files = {
            "docs/ARTICLE.md": "Reviewed first-party source. Local cache: `/Users/private/laptop.txt`\n" + "x" * 1500,
            "data/triz-reference-sources.json": '{"provider_text":"DO_NOT_EXPORT_PROVIDER_TEXT"}\n',
        }
        self.hashes = {}
        for relative, text in self.files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = text.encode("utf-8")
            path.write_bytes(payload)
            self.hashes[relative] = hashlib.sha256(payload).hexdigest()
        self.inventory_path = self.root / "scripts/research_observatory/source-inventory.json"
        self.inventory_path.parent.mkdir(parents=True)
        self.inventory = {
            "schema": "research-observatory-source-inventory-v1",
            "source_base_head": "1" * 40,
            "source_base_tree": "2" * 40,
            "entries": [
                {"path": path, "family": family, "sha256": self.hashes[path]}
                for path, family in (
                    ("docs/ARTICLE.md", "selected_docs"),
                    ("data/triz-reference-sources.json", "triz_reference"),
                )
            ],
        }
        self._write_inventory()
        self._git("init", "-q")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "Test")
        self._git("add", ".")
        self._git("commit", "-qm", "fixture")
        self.head = self._git("rev-parse", "HEAD").strip()
        self.tree = self._git("rev-parse", "HEAD^{tree}").strip()
        self.catalogue = {
            "claims": [{
                "claim_id": "CLM-001", "statement": "A scoped claim",
                "status": "untested", "evidence_level": "E0",
                "last_verified": "2026-01-01", "source": "data/claims.jsonl",
                "private_mapping": "/Users/private/map.json",
            }],
            "observations": [{
                "model": "Example/model", "campaign": "EXP-001 comparative",
                "status": status, "source": "docs/ARTICLE.md",
                "source_paths": ["docs/ARTICLE.md"], "scope": "One scoped observation",
                "notes": "Recorded, not pooled", "metric": None,
                "raw_provider_text": "DO_NOT_EXPORT_PROVIDER_TEXT",
            } for status in STATUS_LABELS] + [{
                "model": "Example/model", "campaign": "A0",
                "status": "future_status", "source": None, "source_paths": [],
                "scope": "Unknown status", "notes": "Must fail closed", "metric": None,
            }],
            "decisions": [{
                "id": "0001", "title": "Decision", "category": "tooling",
                "declared_date": "2026-01-01", "source": "docs/ARTICLE.md",
                "notes": "Indexed", "private_mapping": "/Users/private/map.json",
            }],
            "sources": [{
                "path": path, "sha256": self.hashes[path], "family": family,
                "summary": "Reviewed summary", "declared_date": None,
                "freshness": "local_snapshot", "stale_markers": [],
                "conflict_markers": [], "vcs_state": "tracked_clean",
                "source_scope": "local checkout file",
            } for path, family in (
                ("docs/ARTICLE.md", "selected_docs"),
                ("data/triz-reference-sources.json", "triz_reference"),
            )],
            "warnings": [], "model_names": ["Example/model"],
            "campaign_names": ["EXP-001 comparative", "A0"],
            "source_head": self.head, "source_tree": self.tree,
            "snapshot_sha256": "3" * 64,
        }
        self.loader = mock.patch.object(site_export, "load_observatory", return_value=self.catalogue)
        self.loader.start()
        self.addCleanup(self.loader.stop)

    def tearDown(self):
        self.temp.cleanup()

    def test_rejects_missing_or_mismatched_git_identity(self):
        with self.assertRaises(PermissionError):
            site_export.build_public_payload(self.root, expected_head="", generated_at="2026-09-27T00:00:00Z")
        with self.assertRaises(PermissionError):
            site_export.build_public_payload(self.root, expected_head="a" * 40, generated_at="2026-09-27T00:00:00Z")
        with self.assertRaises(PermissionError):
            site_export.build_public_payload(self.root, expected_head="a" * 64, generated_at="2026-09-27T00:00:00Z")

    def test_rejects_dirty_or_mutated_inventory(self):
        with (self.root / "docs/ARTICLE.md").open("a", encoding="utf-8") as source:
            source.write("dirty\n")
        with self.assertRaises(PermissionError):
            site_export.build_public_payload(self.root, expected_head=self.head, generated_at="2026-09-27T00:00:00Z")

        clean_root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(lambda: __import__("shutil").rmtree(clean_root))
        self._copy_fixture_to(clean_root)
        inv = json.loads((clean_root / "scripts/research_observatory/source-inventory.json").read_text())
        inv["entries"][0]["sha256"] = "f" * 64
        (clean_root / "scripts/research_observatory/source-inventory.json").write_text(json.dumps(inv))
        self._git_at(clean_root, "add", ".")
        self._git_at(clean_root, "commit", "-qm", "mutated inventory")
        bad_head = self._git_at(clean_root, "rev-parse", "HEAD").strip()
        with self.assertRaises(PermissionError):
            site_export.build_public_payload(clean_root, expected_head=bad_head, generated_at="2026-09-27T00:00:00Z")

    def test_rejects_unknown_status_and_future_claim_promotion(self):
        with self.assertRaises(PermissionError):
            site_export.build_public_payload(self.root, expected_head=self.head, generated_at="2026-09-27T00:00:00Z")
        self.catalogue["observations"][-1]["status"] = "not_interpretable"
        self.catalogue["claims"][0]["status"] = "supported"
        self.catalogue["claims"][0]["evidence_level"] = "E1"
        with self.assertRaises(PermissionError):
            site_export.build_public_payload(self.root, expected_head=self.head, generated_at="2026-09-27T00:00:00Z")

    def test_exports_only_reviewed_fields_and_bounded_previews(self):
        del self.catalogue["observations"][-1]
        self.catalogue["sources"][0]["summary"] = "Description copied from `file:///Users/private/notes.md`"
        payload = site_export.build_public_payload(self.root, expected_head=self.head, generated_at="2026-09-27T00:00:00Z")
        self.assertEqual(set(payload), {
            "schema", "generated_at", "build_source", "source_inventory",
            "catalogue_sha256", "claims", "observations", "decisions", "sources",
            "warnings", "model_names", "campaign_names",
        })
        self.assertEqual(set(payload["claims"][0]), {
            "claim_id", "statement", "status", "evidence_level", "last_verified", "source",
        })
        self.assertEqual(set(payload["observations"][0]), {
            "model", "campaign", "status", "source", "source_paths", "scope", "notes", "metric",
        })
        self.assertEqual(set(payload["decisions"][0]), {
            "id", "title", "category", "declared_date", "source", "notes",
        })
        sources = {record["path"]: record for record in payload["sources"]}
        self.assertTrue(all("preview" not in source for source in sources.values()))
        self.assertIn("Reviewed project document", sources["docs/ARTICLE.md"]["summary"])
        serialized = json.dumps(payload)
        self.assertNotIn("DO_NOT_EXPORT_PROVIDER_TEXT", serialized)
        self.assertNotIn("/Users/private", serialized)
        self.assertNotIn("file:", serialized)
        self.assertEqual({item["status"] for item in payload["observations"]}, set(STATUS_LABELS))

    def test_rejects_private_paths_and_unbounded_or_controlled_public_text(self):
        bad_values = (
            "quoted `/Users/private/profile.txt`",
            "provider file file:///Users/private/provider.pdf",
            "nested /private/tmp/export.json",
        )
        for field, value in (
            ("claim", bad_values[0]),
            ("notes", bad_values[1]),
            ("warning", bad_values[2]),
            ("oversized", "x" * 1201),
            ("control", "unsafe\x00text"),
            ("bidi", "unsafe\u202etext"),
        ):
            with self.subTest(field=field):
                original = json.loads(json.dumps(self.catalogue))
                if field in {"claim", "oversized", "control", "bidi"}:
                    self.catalogue["claims"][0]["statement"] = value
                elif field == "notes":
                    self.catalogue["observations"][0]["notes"] = value
                else:
                    self.catalogue["warnings"] = [value]
                with self.assertRaises(PermissionError):
                    site_export.build_public_payload(
                        self.root, expected_head=self.head, generated_at="2026-09-27T00:00:00Z",
                    )
                self.catalogue.clear()
                self.catalogue.update(original)

    def test_requires_utc_rfc3339_generation_time(self):
        for generated_at in (
            "2026-09-27T12:00:00+01:00", "2026-09-27 12:00:00Z",
            "2026-02-30T12:00:00Z", "2026-09-27T12:00:00",
            "2026-09-27T12:00:00Z`/Users/private/file",
        ):
            with self.subTest(generated_at=generated_at), self.assertRaises(PermissionError):
                site_export.build_public_payload(
                    self.root, expected_head=self.head, generated_at=generated_at,
                )

    def test_records_distinct_inventory_and_catalogue_digests(self):
        del self.catalogue["observations"][-1]
        payload = site_export.build_public_payload(self.root, expected_head=self.head, generated_at="2026-09-27T00:00:00Z")
        self.assertEqual(payload["source_inventory"]["sha256"], hashlib.sha256(self.inventory_path.read_bytes()).hexdigest())
        self.assertEqual(payload["catalogue_sha256"], self.catalogue["snapshot_sha256"])
        self.assertNotEqual(payload["source_inventory"]["sha256"], payload["catalogue_sha256"])

    def test_writes_canonical_json_without_overwriting_existing_file(self):
        del self.catalogue["observations"][-1]
        payload = site_export.build_public_payload(
            self.root, expected_head=self.head, generated_at="2026-09-27T00:00:00Z",
        )
        payload["claims"][0]["statement"] = "Café claim"
        destination = self.root / "owned-output"
        destination.mkdir()
        result = site_export.write_public_payload(payload, destination)
        expected = destination / "site-data.json"
        self.assertEqual(result, expected)
        encoded = expected.read_bytes()
        self.assertIn("Café claim".encode("utf-8"), encoded)
        self.assertNotIn(b"\\u00e9", encoded)
        self.assertTrue(encoded.endswith(b"\n"))
        self.assertEqual(json.loads(encoded.decode("utf-8")), payload)
        with self.assertRaises(FileExistsError):
            site_export.write_public_payload(payload, destination)

    def test_writer_rejects_arbitrary_unknown_and_private_payloads(self):
        del self.catalogue["observations"][-1]
        valid = site_export.build_public_payload(
            self.root, expected_head=self.head, generated_at="2026-09-27T00:00:00Z",
        )
        private = json.loads(json.dumps(valid))
        private["claims"][0]["statement"] = "private `/Users/private/key`"
        unknown = json.loads(json.dumps(valid))
        unknown["unreviewed"] = "not allowed"
        bad_schema = json.loads(json.dumps(valid))
        bad_schema["schema"] = "research-observatory-site-v2"
        for index, payload in enumerate((
            {"z": "café"},
            unknown, bad_schema, private,
        )):
            destination = self.root / f"invalid-{index}"
            destination.mkdir()
            with self.subTest(payload=payload), self.assertRaises((PermissionError, TypeError)):
                site_export.write_public_payload(payload, destination)
            self.assertFalse((destination / "site-data.json").exists())

    def test_writer_rejects_file_destination_and_symlinked_parent(self):
        del self.catalogue["observations"][-1]
        payload = site_export.build_public_payload(
            self.root, expected_head=self.head, generated_at="2026-09-27T00:00:00Z",
        )
        file_destination = self.root / "not-a-directory"
        file_destination.write_text("x", encoding="utf-8")
        with self.assertRaises(PermissionError):
            site_export.write_public_payload(payload, file_destination)

        real_directory = self.root / "real-output"
        real_directory.mkdir()
        parent_link = self.root / "linked-output"
        parent_link.symlink_to(real_directory, target_is_directory=True)
        with self.assertRaises(PermissionError):
            site_export.write_public_payload(payload, parent_link)
        self.assertFalse((real_directory / "site-data.json").exists())

    def test_writer_rejects_oversized_serialized_payload(self):
        del self.catalogue["observations"][-1]
        payload = site_export.build_public_payload(
            self.root, expected_head=self.head, generated_at="2026-09-27T00:00:00Z",
        )
        payload["warnings"] = ["w" * 1200 for _ in range(900)]
        destination = self.root / "large-output"
        destination.mkdir()
        with self.assertRaises(PermissionError):
            site_export.write_public_payload(payload, destination)
        self.assertFalse((destination / "site-data.json").exists())

    def _write_inventory(self):
        self.inventory_path.write_text(json.dumps(self.inventory), encoding="utf-8")

    def _copy_fixture_to(self, root):
        for relative, text in self.files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        inventory_path = root / "scripts/research_observatory/source-inventory.json"
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_text(json.dumps(self.inventory), encoding="utf-8")
        self._git_at(root, "init", "-q")
        self._git_at(root, "config", "user.email", "test@example.invalid")
        self._git_at(root, "config", "user.name", "Test")
        self._git_at(root, "add", ".")
        self._git_at(root, "commit", "-qm", "fixture")

    def _git(self, *args):
        return self._git_at(self.root, *args)

    @staticmethod
    def _git_at(root, *args):
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True,
            capture_output=True, text=True,
        ).stdout


if __name__ == "__main__":
    unittest.main()
