from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.research_observatory import observatory_data, site_export
from scripts.research_observatory.observatory_views import STATUS_LABELS


REPOSITORY = Path(__file__).resolve().parents[2]
GENERATED_AT = "2026-09-27T00:00:00Z"
EXPECTED_OUTPUTS = {"index.html", "style.css", "app.mjs", "site-data.json"}


class SiteBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clone_temp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls.clone_temp.name) / "clean-clone"
        subprocess.run(
            ["git", "clone", "--no-hardlinks", "--no-local", str(REPOSITORY), str(cls.repo)],
            check=True, capture_output=True, text=True,
        )
        cls.repo = cls.repo.resolve(strict=True)
        cls.head = subprocess.run(
            ["git", "-C", str(cls.repo), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        cls.oracle = observatory_data.load_observatory(cls.repo, strict_public=True)

    @classmethod
    def tearDownClass(cls):
        cls.clone_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.parent = Path(self.temp.name)
        self.destination = self.parent / "site"

    def tearDown(self):
        self.temp.cleanup()

    def test_build_matches_local_observatory_oracle(self):
        site_export.build_site(
            self.repo, self.destination, expected_head=self.head,
            generated_at=GENERATED_AT,
        )
        first = self._read_bundle(self.destination)
        second_destination = self.parent / "second-site"
        site_export.build_site(
            self.repo, second_destination, expected_head=self.head,
            generated_at=GENERATED_AT,
        )
        second = self._read_bundle(second_destination)
        self.assertEqual(first, second, "fixed timestamp must produce byte-identical bundles")

        payload = json.loads(first["site-data.json"])
        self.assertEqual(payload["claims"], [
            {key: item[key] for key in (
                "claim_id", "statement", "status", "evidence_level", "last_verified", "source",
            )}
            for item in self.oracle["claims"]
        ])
        self.assertEqual(payload["warnings"], self.oracle["warnings"])
        self.assertEqual(len(payload["sources"]), 66)
        self.assertEqual(len(payload["observations"]), 35)
        self.assertTrue({item["status"] for item in payload["observations"]} <= set(STATUS_LABELS))
        oracle_observations = [
            {key: item[key] for key in (
                "model", "campaign", "status", "source", "source_paths", "scope", "notes", "metric",
            )}
            for item in self.oracle["observations"]
        ]
        self.assertEqual(payload["observations"], oracle_observations)
        self.assertEqual(
            [(item["path"], item["sha256"], item["family"]) for item in payload["sources"]],
            [(item["path"], item["sha256"], item["family"]) for item in self.oracle["sources"]],
        )
        self.assertEqual(payload["build_source"], {
            "head": self.head,
            "tree": self.oracle["source_tree"],
        })

        # Browser selectors/view models use the exact exported bytes and must
        # retain the six named views and the reviewed five-stage route.
        model_script = (
            "import fs from 'node:fs'; "
            "import {renderViewModel} from './scripts/research_observatory/site/app.mjs'; "
            "const p=JSON.parse(fs.readFileSync(process.argv[1],'utf8')); "
            "const views=['start','matrix','results','route','decisions','sources']; "
            "const out=views.map(v=>renderViewModel(p,v)); "
            "console.log(JSON.stringify(out.map(x=>({view:x.view,claims:x.claims,warnings:x.warnings,"
            "records:x.records?.length,stages:x.stages?.map(s=>s.title),statuses:x.statuses.map(s=>s.value),"
            "sources:x.sources?.length,decisions:x.decisions?.length}))));"
        )
        view_models = subprocess.run(
            ["node", "--input-type=module", "-e", model_script,
             str(self.destination / "site-data.json")],
            cwd=REPOSITORY, check=True, capture_output=True, text=True,
        ).stdout
        models = json.loads(view_models)
        self.assertEqual([item["view"] for item in models], [
            "start", "matrix", "results", "route", "decisions", "sources",
        ])
        self.assertEqual(
            [{key: claim[key] for key in (
                "claim_id", "statement", "status", "evidence_level", "last_verified", "source",
            )} for claim in models[0]["claims"]],
            payload["claims"],
        )
        self.assertEqual(models[0]["warnings"], payload["warnings"])
        self.assertEqual(models[1]["records"], 35)
        self.assertEqual(set(models[1]["statuses"]), set(STATUS_LABELS))
        self.assertEqual(models[3]["stages"], [
            "Decodability", "Geometry", "Generalization", "Causality", "Compositionality",
        ])
        self.assertEqual(models[5]["sources"], 66)
        self.assertEqual(models[4]["decisions"], len(payload["decisions"]))

    def test_refuses_occupied_or_linked_destination(self):
        occupied = self.parent / "occupied"
        occupied.mkdir()
        sentinel = occupied / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises((FileExistsError, PermissionError)):
            site_export.build_site(
                self.repo, occupied, expected_head=self.head,
                generated_at=GENERATED_AT,
            )
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

        real = self.parent / "real"
        real.mkdir()
        linked = self.parent / "linked"
        linked.symlink_to(real, target_is_directory=True)
        with self.assertRaises((FileExistsError, PermissionError)):
            site_export.build_site(
                self.repo, linked, expected_head=self.head,
                generated_at=GENERATED_AT,
            )
        self.assertEqual(list(real.iterdir()), [])

        self.destination.mkdir()
        with self.assertRaises((FileExistsError, PermissionError)):
            site_export.build_site(
                self.repo, self.destination, expected_head=self.head,
                generated_at=GENERATED_AT,
            )
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_atomic_publish_does_not_replace_a_racing_empty_destination(self):
        staging = self.parent / "staging"
        staging.mkdir()
        marker = staging / "site-data.json"
        marker.write_text("staged", encoding="utf-8")
        destination = self.parent / "racing-destination"
        destination.mkdir()
        # Model another writer creating an empty destination after the fast
        # precheck but before the atomic publish operation.
        with mock.patch.object(site_export.os.path, "lexists", return_value=False):
            with self.assertRaises(FileExistsError):
                site_export._publish_directory_exclusively(staging, destination)
        self.assertTrue(destination.is_dir())
        self.assertEqual(list(destination.iterdir()), [])
        self.assertEqual(marker.read_text(encoding="utf-8"), "staged")

    def test_rejects_unreviewed_external_asset_variants(self):
        unsafe_assets = {
            "index.html": (
                '<link rel="stylesheet" href="./style.css">'
                '<script type="module" src="./app.mjs"></script>'
                "<img src='https://example.invalid/image.png'>"
            ),
            "app.mjs": "fetch('https' + '://example.invalid/data.json')",
        }
        for name, contents in unsafe_assets.items():
            with self.subTest(name=name):
                directory = self.parent / f"asset-{name}"
                directory.mkdir()
                (directory / name).write_text(contents, encoding="utf-8")
                directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    with self.assertRaises(PermissionError):
                        site_export._read_site_asset(directory_fd, name)
                finally:
                    os.close(directory_fd)

    def test_bundle_excludes_private_and_external_assets(self):
        site_export.build_site(
            self.repo, self.destination, expected_head=self.head,
            generated_at=GENERATED_AT,
        )
        bundle = self._read_bundle(self.destination)
        self.assertEqual(set(bundle), EXPECTED_OUTPUTS)
        for name, data in bundle.items():
            path = self.destination / name
            metadata = path.lstat()
            self.assertTrue(path.is_file())
            self.assertEqual(metadata.st_nlink, 1)
            self.assertNotIn(b"/Users/", data)
            self.assertNotIn(b"/private/tmp/", data)
            self.assertNotIn(b"file://", data.lower())
            self.assertNotIn(b"DO_NOT_EXPORT_PROVIDER_TEXT", data)
        self.assertLessEqual(len(bundle["site-data.json"]), 1024 * 1024)
        self.assertNotIn(b".pdf", b"\n".join(bundle.values()).lower())
        self.assertNotIn(b"fonts.googleapis.com", b"\n".join(bundle.values()).lower())
        self.assertNotIn(b"<script src=\"https://", bundle["index.html"].lower())
        self.assertNotIn(b"fetch('https://", bundle["app.mjs"].lower())

    def test_failure_cleans_staging_and_cli_writes_only_new_bundle(self):
        with mock.patch.object(site_export, "_copy_static_assets", side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                site_export.build_site(
                    self.repo, self.destination, expected_head=self.head,
                    generated_at=GENERATED_AT,
                )
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.parent.iterdir()), [])

        command = [
            "python3", "-m", "scripts.research_observatory.site_export",
            "--repo-root", str(self.repo), "--destination", str(self.destination),
            "--expected-head", self.head, "--generated-at", GENERATED_AT,
        ]
        result = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(path.name for path in self.destination.iterdir()), EXPECTED_OUTPUTS)
        collision = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True)
        self.assertNotEqual(collision.returncode, 0)
        self.assertEqual(set(path.name for path in self.destination.iterdir()), EXPECTED_OUTPUTS)

    def _read_bundle(self, directory: Path) -> dict[str, bytes]:
        children = list(directory.iterdir())
        self.assertEqual({path.name for path in children}, EXPECTED_OUTPUTS)
        self.assertTrue(all(path.is_file() and not path.is_symlink() for path in children))
        return {path.name: path.read_bytes() for path in children}


if __name__ == "__main__":
    unittest.main()
