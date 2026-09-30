from __future__ import annotations

import builtins
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/qualification/a0x-target-free-schema-profile-v1-manifest.json"


class A0XTargetFreeSchemaProfileTests(unittest.TestCase):
    def profile_api(self):
        try:
            from scripts.a0x_target_free_schema_profile import (
                ProfileError,
                load_profile_manifest,
                read_instance,
                run_profile,
            )
        except ImportError as exc:  # RED until the profile implementation exists.
            self.fail(f"target-free schema profile API is not implemented: {exc}")
        return ProfileError, load_profile_manifest, read_instance, run_profile

    def test_report_accounts_for_complete_closed_world_without_public_instance_reads(self) -> None:
        _, _, _, run_profile = self.profile_api()
        report = run_profile(ROOT, MANIFEST)

        self.assertEqual("a0x-target-free-schema-profile-v1", report["profile"])
        self.assertEqual(211, report["schema_file_count"])
        self.assertEqual(209, report["schema_definition_count"])
        self.assertEqual(1, report["schema_fragment_count"])
        self.assertEqual(1, report["schema_registry_count"])
        self.assertEqual(155, report["legacy_pair_count"])
        self.assertEqual(3, report["positional_example_count"])
        self.assertEqual(12, report["positional_mutation_count"])
        self.assertEqual(3, report["positional_validated_count"])
        self.assertEqual(12, report["positional_mutation_rejected_count"])
        self.assertEqual(0, report["validated_public_count"])
        self.assertEqual(4, report["deferred_protected_count"])
        self.assertEqual(14, report["excluded_sensitive_count"])
        self.assertEqual(137, report["excluded_role_unverified_count"])
        synthetic = report["validated_synthetic"]
        self.assertEqual(2, synthetic["source_count"])
        self.assertEqual(4, synthetic["schema_count"])
        self.assertEqual(17, synthetic["case_count"])
        self.assertEqual(4, synthetic["valid_case_count"])
        self.assertEqual(13, synthetic["invalid_case_count"])
        self.assertEqual({"protected_schema": 1, "legacy_positional": 3}, synthetic["valid_cases"])
        self.assertEqual({"protected_schema": 1, "legacy_mutations": 12}, synthetic["invalid_cases"])
        self.assertFalse(report["real_target_conformance_verified"])
        self.assertFalse(report["full_repository_schema_validation"])

    def test_manifest_classifies_all_211_schema_inputs_and_ref_closure(self) -> None:
        ProfileError, load_profile_manifest, read_instance, run_profile = self.profile_api()
        manifest = load_profile_manifest(ROOT, MANIFEST)
        schema_rows = manifest["schema_files"]
        self.assertEqual(211, len(schema_rows))
        self.assertEqual(209, sum(row[1] == "draft_2020_12_schema" for row in schema_rows))
        self.assertEqual(1, sum(row[1] == "schema_fragment" for row in schema_rows))
        self.assertEqual(1, sum(row[1] == "projection_registry" for row in schema_rows))
        self.assertEqual(155, manifest["legacy_pair_count"])
        pairs = manifest["legacy_pairs"]
        self.assertEqual(155, len(pairs))
        self.assertTrue(all({"role", "disposition", "reason", "evidence"} <= set(row) for row in pairs))
        direct_reads = manifest["direct_root_read_literals"]
        self.assertEqual(11, len(direct_reads))
        common_fields = {"path", "role", "disposition", "reason", "evidence"}
        for row in direct_reads:
            expected_fields = common_fields | ({"schema_binding"} if row["role"] == "schema_definition" else set())
            self.assertEqual(expected_fields, set(row))
        self.assertTrue(all(row["reason"] and row["evidence"] for row in direct_reads))
        self.assertTrue(all(row["reason"] and row["evidence"] for row in pairs))
        lab04 = [row for row in direct_reads if row["path"] == "schemas/lab04-result.schema.json"]
        self.assertEqual(1, len(lab04))
        self.assertEqual("schema_definition", lab04[0]["role"])
        self.assertEqual("validated_schema_definition", lab04[0]["disposition"])
        self.assertEqual("schemas/lab04-result.schema.json", lab04[0]["schema_binding"]["path"])
        self.assertEqual(64, len(lab04[0]["schema_binding"]["sha256"]))
        self.assertNotIn("schemas/lab04-result.schema.json",
                         manifest["instance_dispositions"]["validated_public"])
        with mock.patch("os.open", side_effect=AssertionError("schema literal cannot authorize instance read")), \
             self.assertRaises(ProfileError):
            read_instance(ROOT, manifest, "schemas/lab04-result.schema.json")
        self.assertEqual(3, manifest["positional_examples"]["count"])
        self.assertEqual(12, manifest["positional_mutations"]["count"])
        self.assertEqual(28, manifest["local_references"]["projection_count"])
        refs = manifest["local_references"]["entries"]
        self.assertEqual(manifest["local_references"]["count"], len(refs))
        self.assertGreater(len(refs), 0)
        self.assertTrue(all(row[1].startswith("#/") for row in refs))
        report = run_profile(ROOT, MANIFEST)
        self.assertEqual(len(refs), report["local_schema_reference_count"])

    def test_tampered_manifest_cannot_expand_public_instance_allowlist(self) -> None:
        ProfileError, load_profile_manifest, read_instance, _ = self.profile_api()
        manifest = load_profile_manifest(ROOT, MANIFEST)
        tampered = json.loads(json.dumps(manifest))
        candidate = "data/registry.json"
        tampered["instance_dispositions"]["validated_public"] = [
            {"path": candidate, "sha256": "a" * 64}
        ]
        attempted: list[str] = []
        real_open = os.open

        def guarded_open(path, *args, **kwargs):
            text = str(path)
            if text.endswith(candidate):
                attempted.append(text)
                raise AssertionError("unapproved instance open attempted")
            return real_open(path, *args, **kwargs)

        with mock.patch("os.open", side_effect=guarded_open), self.assertRaises(ProfileError):
            read_instance(ROOT, tampered, candidate)
        self.assertEqual([], attempted)

    def test_complete_profile_never_touches_protected_or_excluded_instance_paths(self) -> None:
        _, load_profile_manifest, _, run_profile = self.profile_api()
        manifest = load_profile_manifest(ROOT, MANIFEST)
        forbidden = tuple(
            [row[0] for row in manifest["instance_dispositions"]["deferred_protected"]]
            + manifest["instance_dispositions"]["excluded_sensitive_role_unverified"]
            + [row["instance"] for row in manifest["legacy_pairs"]]
        )
        forbidden_suffixes = tuple(sorted(set(forbidden)))
        attempted: list[str] = []

        def guard(original):
            def checked(path, *args, **kwargs):
                text = str(path)
                if any(text.endswith(suffix) for suffix in forbidden_suffixes):
                    attempted.append(text)
                    raise AssertionError(f"profile attempted excluded input access: {text}")
                return original(path, *args, **kwargs)
            return checked

        real_os_open = os.open
        real_os_dup = os.dup
        descriptor_paths: dict[int, str] = {}

        def guarded_os_open(path, flags, mode=0o777, *, dir_fd=None):
            component = os.fspath(path)
            parent = descriptor_paths.get(dir_fd, "<unknown-dirfd>") if dir_fd is not None else ""
            candidate = os.path.join(parent, component) if dir_fd is not None else component
            normalized = os.path.normpath(candidate)
            if any(normalized.endswith(suffix) for suffix in forbidden_suffixes):
                attempted.append(normalized)
                raise AssertionError(f"descriptor-relative open attempted excluded input: {normalized}")
            descriptor = real_os_open(path, flags, mode, dir_fd=dir_fd)
            if flags & getattr(os, "O_DIRECTORY", 0):
                descriptor_paths[descriptor] = normalized
            return descriptor

        def guarded_os_dup(descriptor):
            duplicate = real_os_dup(descriptor)
            if descriptor in descriptor_paths:
                descriptor_paths[duplicate] = descriptor_paths[descriptor]
            return duplicate

        with (
            mock.patch.object(Path, "lstat", new=guard(Path.lstat)),
            mock.patch.object(Path, "stat", new=guard(Path.stat)),
            mock.patch.object(Path, "open", new=guard(Path.open)),
            mock.patch.object(Path, "read_bytes", new=guard(Path.read_bytes)),
            mock.patch.object(Path, "read_text", new=guard(Path.read_text)),
            mock.patch("builtins.open", new=guard(builtins.open)),
            mock.patch("os.open", side_effect=guarded_os_open),
            mock.patch("os.dup", side_effect=guarded_os_dup),
        ):
            report = run_profile(ROOT, MANIFEST)
        self.assertEqual("a0x-target-free-schema-profile-v1", report["profile"])
        self.assertEqual([], attempted)

    def test_denied_paths_are_rejected_before_any_filesystem_access(self) -> None:
        ProfileError, load_profile_manifest, read_instance, _ = self.profile_api()
        manifest = load_profile_manifest(ROOT, MANIFEST)
        denied = tuple(
            [row[0] for row in manifest["instance_dispositions"]["deferred_protected"]]
            + manifest["instance_dispositions"]["excluded_sensitive_role_unverified"]
        )
        with (
            mock.patch.object(builtins, "open", side_effect=AssertionError("open attempted")),
            mock.patch.object(Path, "open", side_effect=AssertionError("Path.open attempted")),
            mock.patch.object(Path, "stat", side_effect=AssertionError("Path.stat attempted")),
            mock.patch.object(Path, "read_bytes", side_effect=AssertionError("read_bytes attempted")),
            mock.patch.object(Path, "read_text", side_effect=AssertionError("read_text attempted")),
        ):
            for relative in denied:
                with self.subTest(path=relative), self.assertRaises(ProfileError):
                    read_instance(ROOT, manifest, relative)

    def test_unknown_and_traversal_paths_fail_before_filesystem_access(self) -> None:
        ProfileError, load_profile_manifest, read_instance, _ = self.profile_api()
        manifest = load_profile_manifest(ROOT, MANIFEST)
        for relative in ("results/not-in-manifest.json", "../data/a0/sealed-targets/targets.jsonl", "/etc/passwd"):
            with self.subTest(path=relative), mock.patch.object(
                Path, "stat", side_effect=AssertionError("Path.stat attempted")
            ), self.assertRaises(ProfileError):
                read_instance(ROOT, manifest, relative)

    def test_external_and_unresolved_schema_references_fail_closed(self) -> None:
        ProfileError, *_ = self.profile_api()
        from scripts.a0x_target_free_schema_profile import _pointer

        with self.assertRaises(ProfileError):
            _pointer({"$defs": {"ok": {"type": "string"}}}, "https://example.invalid/schema.json#/x")
        with self.assertRaises(ProfileError):
            _pointer({"$defs": {"ok": {"type": "string"}}}, "#/$defs/missing")

    def test_duplicate_json_object_keys_fail_closed(self) -> None:
        ProfileError, *_ = self.profile_api()
        from scripts.a0x_target_free_schema_profile import _json_bytes

        with self.assertRaises(ProfileError):
            _json_bytes(b'{"profile":"one","profile":"two"}', "synthetic")

    def test_duplicate_pairs_and_manifest_drift_fail_closed(self) -> None:
        ProfileError, load_profile_manifest, _, run_profile = self.profile_api()
        manifest = load_profile_manifest(ROOT, MANIFEST)
        duplicated = dict(manifest)
        duplicated["legacy_pairs"] = list(manifest["legacy_pairs"]) + [manifest["legacy_pairs"][0]]
        with self.assertRaises(ProfileError):
            run_profile(ROOT, manifest=duplicated)

        drifted = dict(manifest)
        drifted["legacy_pairs_sha256"] = "0" * 64
        with self.assertRaises(ProfileError):
            run_profile(ROOT, manifest=drifted)

    def test_every_protected_target_schema_has_synthetic_positive_and_negative_coverage(self) -> None:
        _, _, _, run_profile = self.profile_api()
        report = run_profile(ROOT, MANIFEST)
        coverage = report["protected_schema_synthetic_coverage"]
        self.assertEqual({"schemas/a0-procedural-target.schema.json"}, set(coverage))
        for schema_path, result in coverage.items():
            with self.subTest(schema=schema_path):
                self.assertTrue(result["valid_instance_accepted"])
                self.assertTrue(result["invalid_instance_rejected"])
                self.assertTrue(result["fixture_source"] == "in_memory_synthetic")

    def test_package_initializer_hash_is_bound_before_latent_triz_import(self) -> None:
        ProfileError, *_ = self.profile_api()
        from scripts import a0x_target_free_schema_profile as profile

        before = {name for name in sys.modules
                  if name == "latent_triz" or name.startswith("latent_triz.")}
        self.assertEqual(set(), before)
        with mock.patch.dict(profile.EXPECTED_SOURCE_HASHES,
                             {profile.PACKAGE_INIT: "0" * 64}):
            with self.assertRaises(ProfileError):
                profile.build_manifest(ROOT)
        after = {name for name in sys.modules
                 if name == "latent_triz" or name.startswith("latent_triz.")}
        self.assertEqual(before, after)

    def test_replaced_bound_module_fails_and_cleanup_preserves_replacement(self) -> None:
        ProfileError, *_ = self.profile_api()
        from scripts import a0x_target_free_schema_profile as profile

        replacement = types.ModuleType("latent_triz.a0x_pair")
        original_load = profile._BoundExecutionContext.load
        injected: list[types.ModuleType] = []

        def replace_after_load(context, names):
            result = original_load(context, names)
            if "latent_triz.a0x_pair" in names:
                sys.modules["latent_triz.a0x_pair"] = replacement
                injected.append(replacement)
            return result

        with mock.patch.object(profile._BoundExecutionContext, "load", new=replace_after_load), \
             self.assertRaisesRegex(ProfileError, "replacement detected"):
            profile.build_manifest(ROOT)
        try:
            self.assertEqual([replacement], injected)
            self.assertIs(replacement, sys.modules.get("latent_triz.a0x_pair"))
        finally:
            if sys.modules.get("latent_triz.a0x_pair") is replacement:
                del sys.modules["latent_triz.a0x_pair"]
            if sys.modules.get("latent_triz") is not None:
                del sys.modules["latent_triz"]

    def test_preloaded_latent_namespace_is_rejected_before_any_source_io(self) -> None:
        ProfileError, *_ = self.profile_api()
        from scripts import a0x_target_free_schema_profile as profile

        for name in ("latent_triz", "latent_triz.a0x_pair"):
            forged = types.ModuleType(name)
            forged.__a0x_bound_root__ = str(ROOT)
            forged.__a0x_bound_sha256__ = profile.EXPECTED_SOURCE_HASHES.get(
                profile.PACKAGE_INIT, "0" * 64
            )
            with self.subTest(name=name), mock.patch.dict(sys.modules, {name: forged}), \
                 mock.patch("os.open", side_effect=AssertionError("source I/O before namespace refusal")), \
                 self.assertRaises(ProfileError):
                profile.build_manifest(ROOT)

    def test_unknown_schema_looking_literal_is_not_admitted_as_schema(self) -> None:
        _, *_ = self.profile_api()
        from scripts.a0x_target_free_schema_profile import _direct_literal_row

        row = _direct_literal_row("schemas/not-in-manifest.schema.json", {})
        self.assertEqual("unresolved_schema_candidate", row["role"])
        self.assertEqual("excluded_role_unverified", row["disposition"])
        self.assertNotIn("schema_binding", row)

    def test_descriptor_reader_rejects_parent_and_leaf_symlink_substitution(self) -> None:
        ProfileError, *_ = self.profile_api()
        from scripts.a0x_target_free_schema_profile import _read_bytes

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            root.mkdir()
            external = base / "external"
            external.mkdir()
            (external / "payload.json").write_bytes(b'{"synthetic":true}')
            (root / "alias").symlink_to(external, target_is_directory=True)
            with self.assertRaises(ProfileError):
                _read_bytes(root, "alias/payload.json")
            (root / "safe").mkdir()
            (root / "safe" / "payload.json").symlink_to(external / "payload.json")
            with self.assertRaises(ProfileError):
                _read_bytes(root, "safe/payload.json")


if __name__ == "__main__":
    unittest.main()
