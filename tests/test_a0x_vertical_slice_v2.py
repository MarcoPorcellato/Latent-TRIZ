from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from latent_triz.a0x_contract import (
    VERTICAL_PACKAGE_COMMITMENT_PROFILE,
    V2_MEMBER_NAMES,
    build_vertical_package_commitment,
    validate_vertical_package_commitment,
)
from latent_triz.a0x_vertical_slice import (
    A0XVerticalSliceError,
    V2_OUTPUT_EXISTS,
    V2_PUBLICATION_OWNERSHIP_LOST,
    V2_VALIDATION_FAILED,
    VerticalPackageBinding,
    VerticalRuntimePackageRequest,
    generate_vertical_runtime_package,
    load_vertical_runtime_package,
)
from tests.test_a0x_vertical_slice import HEAD, TREE, ROOT, _copy_file, _publish_at, _synthetic_repository


class A0XVerticalSliceV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repository"
        self.root.mkdir()
        _synthetic_repository(self.root)
        _copy_file(ROOT, self.root, "schemas/a0x-vertical-slice-manifest-v2.schema.json")
        _copy_file(ROOT, self.root, "schemas/a0x-vertical-package-commitment-v2.schema.json")
        self.tree_patch = mock.patch(
            "latent_triz.a0x_vertical_slice._git_tree_for_head", return_value=TREE,
        )
        self.publish_patch = mock.patch(
            "latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at", new=_publish_at,
        )
        self.checkout_patch = mock.patch(
            "latent_triz.a0x_vertical_slice._checkout_state", return_value=(HEAD, TREE, True),
        )
        self.tree_patch.start()
        self.publish_patch.start()
        self.checkout_patch.start()

    def tearDown(self) -> None:
        self.checkout_patch.stop()
        self.publish_patch.stop()
        self.tree_patch.stop()
        self.temporary.cleanup()

    def request(self, *, tree: str = TREE) -> VerticalRuntimePackageRequest:
        return VerticalRuntimePackageRequest(
            qualified_source_head=HEAD,
            qualified_source_tree=tree,
            leg=__import__("latent_triz.a0x_contract", fromlist=["Leg"]).Leg.A0,
            model_key="smollm2_360m",
            output_root=f".a0x-runtime/p0/v2/{HEAD}/{tree}/a0/smollm2_360m",
            authorization_id="p0-auth-test-01",
            attempt_id="p0-attempt-test-01",
        )

    def binding(self) -> VerticalPackageBinding:
        return generate_vertical_runtime_package(self.root, self.request())

    def test_v2_api_is_available(self) -> None:
        self.assertEqual("a0x-vertical-package-commitment-v2", VERTICAL_PACKAGE_COMMITMENT_PROFILE)
        self.assertEqual(
            (
                "protocol.json",
                "implementation.json",
                "freeze.json",
                "approval-dossier.json",
                "slice-manifest.json",
            ),
            V2_MEMBER_NAMES,
        )
        self.assertTrue(VerticalRuntimePackageRequest)
        self.assertTrue(VerticalPackageBinding)
        self.assertTrue(generate_vertical_runtime_package)
        self.assertTrue(load_vertical_runtime_package)
        self.assertTrue(build_vertical_package_commitment)
        self.assertTrue(validate_vertical_package_commitment)

    def test_generation_publishes_one_atomic_v2_envelope_and_loads_it(self) -> None:
        binding = self.binding()
        envelope = self.root / binding.envelope_path
        package = self.root / binding.package_path
        self.assertEqual({envelope / "package", envelope / "p0-commitment.json"}, set(envelope.iterdir()))
        self.assertEqual(set(V2_MEMBER_NAMES), {path.name for path in package.iterdir()})
        self.assertEqual(HEAD, binding.qualified_source_head)
        self.assertEqual(TREE, binding.qualified_source_tree)
        loaded = load_vertical_runtime_package(self.root, binding)
        self.assertEqual(binding.package_commitment_sha256, loaded["package_commitment_sha256"])
        self.assertEqual(binding.dossier_sha256, loaded["dossier_sha256"])

    def test_commitment_rejects_reordered_members_and_changed_hash(self) -> None:
        binding = self.binding()
        commitment = json.loads((self.root / binding.commitment_path).read_text(encoding="utf-8"))
        for mutate in (
            lambda value: value.__setitem__("members", list(reversed(value["members"]))),
            lambda value: value["members"][0].__setitem__("sha256", "f" * 64),
            lambda value: value["qualified_source"].__setitem__("tree", "c" * 40),
        ):
            rejected = copy.deepcopy(commitment)
            mutate(rejected)
            with self.subTest(rejected=rejected), self.assertRaisesRegex(
                Exception, "vertical package|commitment",
            ):
                validate_vertical_package_commitment(rejected)

    def test_loader_refuses_member_drift_and_occupied_output(self) -> None:
        binding = self.binding()
        protocol = self.root / binding.package_path / "protocol.json"
        protocol.write_bytes(protocol.read_bytes() + b" ")
        with self.assertRaisesRegex(A0XVerticalSliceError, V2_VALIDATION_FAILED):
            load_vertical_runtime_package(self.root, binding)

        occupied = self.request()
        (self.root / occupied.output_root).mkdir(parents=True, exist_ok=True)
        with self.assertRaisesRegex(A0XVerticalSliceError, V2_OUTPUT_EXISTS):
            generate_vertical_runtime_package(self.root, occupied)

    def test_loader_refuses_symlink_hardlink_extra_and_missing_members(self) -> None:
        mutations = ("symlink", "hardlink", "extra", "missing")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                binding = self.binding()
                package = self.root / binding.package_path
                protocol = package / "protocol.json"
                if mutation == "symlink":
                    protocol.unlink()
                    protocol.symlink_to("freeze.json")
                elif mutation == "hardlink":
                    replacement = package / "replacement.json"
                    os.link(protocol, replacement)
                elif mutation == "extra":
                    (package / "extra.json").write_bytes(b"{}\n")
                else:
                    protocol.unlink()
                with self.assertRaisesRegex(A0XVerticalSliceError, V2_VALIDATION_FAILED):
                    load_vertical_runtime_package(self.root, binding)
                shutil.rmtree(self.root / binding.envelope_path)

    def test_loader_refuses_v1_substitution_and_wrong_source_binding(self) -> None:
        binding = self.binding()
        v1_binding = VerticalPackageBinding(
            **{**binding.__dict__, "package_path": binding.package_path.replace(".a0x-runtime/p0/v2", "experiments/a0x-six-model/vertical-slices")},
        )
        wrong_tree_binding = VerticalPackageBinding(
            **{**binding.__dict__, "qualified_source_tree": "c" * 40},
        )
        for rejected in (v1_binding, wrong_tree_binding):
            with self.subTest(rejected=rejected), self.assertRaisesRegex(A0XVerticalSliceError, V2_VALIDATION_FAILED):
                load_vertical_runtime_package(self.root, rejected)

    def test_generation_preserves_replacement_after_post_publish_ownership_loss(self) -> None:
        def replace(transaction: object) -> None:
            parent = transaction.parent
            os.rename(parent.destination_name, "moved", src_dir_fd=parent.fd, dst_dir_fd=parent.fd)
            os.mkdir(parent.destination_name, dir_fd=parent.fd)

        with mock.patch("latent_triz.a0x_vertical_slice._after_publish", new=replace):
            with self.assertRaisesRegex(A0XVerticalSliceError, V2_PUBLICATION_OWNERSHIP_LOST):
                self.binding()
        envelope = self.root / self.request().output_root
        self.assertTrue(envelope.is_dir())
        self.assertTrue((envelope.parent / "moved").is_dir())

    def test_generation_cleans_only_owned_stage_after_publish_failure(self) -> None:
        with mock.patch(
            "latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at",
            side_effect=OSError("publish failed"),
        ):
            with self.assertRaisesRegex(A0XVerticalSliceError, "V2_PUBLICATION_FAILED"):
                self.binding()
        parent = (self.root / self.request().output_root).parent
        self.assertEqual([], [path for path in parent.iterdir() if path.name.startswith(".a0x-vertical-slice-")])
