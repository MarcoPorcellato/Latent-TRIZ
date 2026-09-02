from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import latent_triz.a0x_vertical_slice as vertical
from latent_triz.a0x_contract import Leg
from latent_triz.a0x_freeze import _IMPLEMENTATION_PATHS, _LEG_SOURCES
from latent_triz.a0x_vertical_slice import (
    OUTPUT_EXISTS,
    PUBLICATION_FAILED,
    PUBLICATION_OWNERSHIP_LOST,
    PUBLICATION_UNSUPPORTED,
    A0XVerticalSliceError,
    VerticalSliceRequest,
    generate_vertical_slice,
    load_vertical_slice,
)


ROOT = Path(__file__).resolve().parents[1]
HEAD = "a" * 40
TREE = "b" * 40
FINAL_NAMES = {
    "protocol.json",
    "implementation.json",
    "freeze.json",
    "approval-dossier.json",
    "slice-manifest.json",
}


def _publish_at(parent_fd: int, stage_name: str, destination_name: str) -> None:
    os.rename(stage_name, destination_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)


def _copy_file(source_root: Path, destination_root: Path, relative: str) -> None:
    destination = destination_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_root / relative, destination)


def _synthetic_repository(destination: Path) -> None:
    paths = set(_IMPLEMENTATION_PATHS)
    paths.update(
        {
            "experiments/a0x-six-model/model-registry.json",
            "experiments/a0x-six-model/material-execution-contract.json",
            "schemas/a0x-authorization-dossier.schema.json",
            "schemas/a0x-freeze-manifest.schema.json",
            "schemas/a0x-implementation.schema.json",
            "schemas/a0x-protocol.schema.json",
            "schemas/a0x-vertical-slice-manifest.schema.json",
        }
    )
    for spec in _LEG_SOURCES.values():
        paths.update(str(spec[name]) for name in ("protocol", "implementation", "protected_tree", "selection"))
    registry = json.loads((ROOT / "experiments/a0x-six-model/model-registry.json").read_text())
    paths.update(f"experiments/a0x-six-model/{relative}" for relative in registry["cards"])
    for relative in sorted(paths):
        _copy_file(ROOT, destination, relative)
    for relative in (
        "experiments/a0x-six-model/approval-dossiers",
        "experiments/a0x-six-model/freeze",
    ):
        shutil.copytree(ROOT / relative, destination / relative)


def _tree_bytes(root: Path, relative: str) -> dict[str, bytes]:
    base = root / relative
    return {
        path.relative_to(base).as_posix(): path.read_bytes()
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


class A0XVerticalSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repository"
        self.root.mkdir()
        _synthetic_repository(self.root)
        self.historical = {
            relative: _tree_bytes(self.root, relative)
            for relative in (
                "experiments/a0x-six-model/approval-dossiers",
                "experiments/a0x-six-model/freeze",
            )
        }
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
        for relative, expected in self.historical.items():
            self.assertEqual(expected, _tree_bytes(self.root, relative))
        self.publish_patch.stop()
        self.tree_patch.stop()
        self.checkout_patch.stop()
        self.temporary.cleanup()

    def request(self, leg: str = "a0", model_key: str = "smollm2_360m", head: str = HEAD) -> VerticalSliceRequest:
        output_root = f"experiments/a0x-six-model/vertical-slices/{head}/{leg}/{model_key}"
        return VerticalSliceRequest(
            leg=Leg(leg),
            model_key=model_key,
            implementation_source_head=head,
            output_root=output_root,
        )

    def package(self, leg: str = "a0", model_key: str = "smollm2_360m") -> Path:
        return self.root / self.request(leg, model_key).output_root

    def test_pair_package_contains_only_one_selected_leg_and_model(self) -> None:
        receipt = generate_vertical_slice(self.root, self.request())
        package = self.package()
        self.assertEqual(5, len(receipt["written"]))
        self.assertEqual("a0", receipt["pair"]["leg"])
        self.assertEqual("smollm2_360m", receipt["pair"]["model_key"])
        self.assertEqual(FINAL_NAMES, {path.name for path in package.iterdir()})
        loaded = load_vertical_slice(self.root, f"{self.request().output_root}/approval-dossier.json")
        self.assertEqual(receipt["pair"], loaded["pair"])
        self.assertEqual(HEAD, receipt["implementation_source_head"])
        self.assertEqual(TREE, receipt["implementation_source_tree"])
        self.assertEqual(set(FINAL_NAMES - {"slice-manifest.json"}), set(loaded["manifest"]["members"]))
        self.assertNotIn("slice-manifest.json", loaded["manifest"]["members"])
        self.assertEqual(0, receipt["sealed_target_content_reads"])
        self.assertEqual(0, receipt["model_loads"])
        self.assertEqual(0, receipt["tokenizer_constructions"])
        self.assertEqual(0, receipt["ccp_invocations"])
        self.assertEqual(0, receipt["network_operations"])

    def test_staging_directory_and_members_are_private_before_publish(self) -> None:
        observed: dict[str, object] = {}

        def inspect(transaction: Any) -> None:
            stage_fd = transaction.stage_fd
            observed["directory_mode"] = stat.S_IMODE(os.fstat(stage_fd).st_mode)
            observed["names"] = set(os.listdir(stage_fd))
            observed["file_modes"] = {
                name: stat.S_IMODE(os.stat(name, dir_fd=stage_fd, follow_symlinks=False).st_mode)
                for name in os.listdir(stage_fd)
            }

        with mock.patch("latent_triz.a0x_vertical_slice._before_publish", new=inspect):
            generate_vertical_slice(self.root, self.request())
        self.assertEqual(0o700, observed["directory_mode"])
        self.assertEqual(FINAL_NAMES, observed["names"])
        self.assertEqual({name: 0o600 for name in FINAL_NAMES}, observed["file_modes"])

    def test_selector_rejects_unknown_model_or_noncanonical_head(self) -> None:
        cases = (
            self.request(model_key="unknown"),
            self.request(head="short"),
            VerticalSliceRequest(Leg.A0, "smollm2_360m", HEAD, "../escape"),
            VerticalSliceRequest(Leg.A0, "smollm2_360m", HEAD, self.request().output_root + "/extra"),
        )
        for request in cases:
            with self.subTest(request=request), self.assertRaises(A0XVerticalSliceError):
                generate_vertical_slice(self.root, request)

    def test_generation_rejects_mismatched_or_dirty_checkout_before_input_reads(self) -> None:
        states = (
            ("head", ("c" * 40, TREE, True)),
            ("tree", (HEAD, "c" * 40, True)),
            ("dirty", (HEAD, TREE, False)),
        )
        for label, state in states:
            with self.subTest(label=label):
                with mock.patch("latent_triz.a0x_vertical_slice._checkout_state", return_value=state):
                    with mock.patch(
                        "latent_triz.a0x_vertical_slice._after_prerequisite_read",
                    ) as prerequisite_read:
                        with self.assertRaises(A0XVerticalSliceError):
                            generate_vertical_slice(self.root, self.request())
                prerequisite_read.assert_not_called()
                self.assertFalse(self.package().exists())

    def test_generation_rechecks_checkout_immediately_before_publish(self) -> None:
        with mock.patch(
            "latent_triz.a0x_vertical_slice._checkout_state",
            side_effect=((HEAD, TREE, True), (HEAD, TREE, False)),
        ) as checkout:
            with mock.patch(
                "latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at",
            ) as publisher:
                with self.assertRaises(A0XVerticalSliceError):
                    generate_vertical_slice(self.root, self.request())
        self.assertEqual(2, checkout.call_count)
        publisher.assert_not_called()
        self.assertFalse(self.package().exists())

    def test_generation_binds_real_clean_git_checkout_and_allows_only_owned_stage(self) -> None:
        self.checkout_patch.stop()
        self.tree_patch.stop()
        try:
            commands = (
                ("init", "-q"),
                ("config", "user.name", "A0X Synthetic Test"),
                ("config", "user.email", "a0x@example.invalid"),
                ("add", "-A"),
                ("commit", "-q", "-m", "synthetic prerequisite fixture"),
            )
            for arguments in commands:
                subprocess.run(
                    ("/usr/bin/git", "-C", str(self.root), *arguments),
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={"PATH": "/usr/bin:/bin"},
                )
            head = subprocess.check_output(
                ("/usr/bin/git", "-C", str(self.root), "rev-parse", "HEAD"),
                env={"PATH": "/usr/bin:/bin"},
                text=True,
            ).strip()
            tree = subprocess.check_output(
                ("/usr/bin/git", "-C", str(self.root), "rev-parse", "HEAD^{tree}"),
                env={"PATH": "/usr/bin:/bin"},
                text=True,
            ).strip()
            request = self.request(head=head)
            receipt = generate_vertical_slice(self.root, request)
            self.assertEqual(head, receipt["implementation_source_head"])
            self.assertEqual(tree, receipt["implementation_source_tree"])
        finally:
            self.tree_patch.start()
            self.checkout_patch.start()

    def test_selector_rejects_missing_or_duplicate_registry_model_key(self) -> None:
        card_path = self.root / "experiments/a0x-six-model/model-cards/qwen2_5_0_5b.json"
        original = card_path.read_bytes()
        for mutation in ("missing", "duplicate"):
            with self.subTest(mutation=mutation):
                card = json.loads(original)
                if mutation == "missing":
                    del card["model_key"]
                else:
                    card["model_key"] = "smollm2_360m"
                card_path.write_bytes(_canonical(card))
                with self.assertRaises(A0XVerticalSliceError):
                    generate_vertical_slice(self.root, self.request())
                card_path.write_bytes(original)

    def test_selector_rejects_card_metadata_disagreement(self) -> None:
        card_path = self.root / "experiments/a0x-six-model/model-cards/smollm2_360m.json"
        card = json.loads(card_path.read_text())
        card["model_key"] = "gpt2"
        card_path.write_bytes(_canonical(card))
        with self.assertRaises(A0XVerticalSliceError):
            generate_vertical_slice(self.root, self.request())

    def test_generation_rejects_symlink_or_hardlink_prerequisite(self) -> None:
        card_path = self.root / "experiments/a0x-six-model/model-cards/smollm2_360m.json"
        original = card_path.read_bytes()
        for mutation in ("symlink", "hardlink"):
            with self.subTest(mutation=mutation):
                card_path.unlink()
                source = card_path.with_name(f"source-{mutation}.json")
                source.write_bytes(original)
                if mutation == "symlink":
                    card_path.symlink_to(source.name)
                else:
                    os.link(source, card_path)
                with self.assertRaises(A0XVerticalSliceError):
                    generate_vertical_slice(self.root, self.request())
                card_path.unlink()
                source.unlink()
                card_path.write_bytes(original)

    def test_prerequisite_parse_and_hash_use_same_descriptor_bytes(self) -> None:
        relative = str(_LEG_SOURCES[Leg.A0]["protocol"])
        path = self.root / relative
        original = path.read_bytes()
        original_value = json.loads(original)
        replacement = json.loads(original)
        replacement["calibration_families_per_domain"] = 999

        def replace_after_read(observed_relative: str, _raw: bytes) -> None:
            if observed_relative == relative:
                path.write_bytes(_canonical(replacement))

        with mock.patch(
            "latent_triz.a0x_vertical_slice._after_prerequisite_read",
            side_effect=replace_after_read,
        ):
            generate_vertical_slice(self.root, self.request())
        protocol = json.loads((self.package() / "protocol.json").read_text())
        self.assertEqual(hashlib.sha256(original).hexdigest(), protocol["source_protocol_raw_sha256"])
        self.assertEqual(
            original_value["calibration_families_per_domain"],
            protocol["inherited_rules"]["calibration_families_per_domain"],
        )

    def test_occupied_destination_refuses_without_overwrite(self) -> None:
        package = self.package()
        package.mkdir(parents=True)
        marker = package / "owned.txt"
        marker.write_bytes(b"keep")
        with self.assertRaises(A0XVerticalSliceError) as caught:
            generate_vertical_slice(self.root, self.request())
        self.assertEqual(OUTPUT_EXISTS, caught.exception.code)
        self.assertEqual(b"keep", marker.read_bytes())

    def test_generation_rejects_symlinked_namespace_parent(self) -> None:
        campaign = self.root / "experiments/a0x-six-model"
        outside = self.root / "outside"
        outside.mkdir()
        (campaign / "vertical-slices").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(A0XVerticalSliceError):
            generate_vertical_slice(self.root, self.request())
        self.assertEqual([], list(outside.iterdir()))

    def test_load_rejects_noncanonical_dossier_path(self) -> None:
        generate_vertical_slice(self.root, self.request())
        invalid = (
            "../approval-dossier.json",
            self.request().output_root + "/protocol.json",
            self.request().output_root.replace(HEAD, "c" * 40) + "/approval-dossier.json",
        )
        for relative in invalid:
            with self.subTest(relative=relative), self.assertRaises(A0XVerticalSliceError):
                load_vertical_slice(self.root, relative)

    def test_load_rejects_mismatched_or_dirty_checkout_before_package_reads(self) -> None:
        generate_vertical_slice(self.root, self.request())
        dossier = f"{self.request().output_root}/approval-dossier.json"
        states = (
            ("head", ("c" * 40, TREE, True)),
            ("tree", (HEAD, "c" * 40, True)),
            ("dirty", (HEAD, TREE, False)),
        )
        for label, state in states:
            with self.subTest(label=label):
                with mock.patch("latent_triz.a0x_vertical_slice._checkout_state", return_value=state):
                    with mock.patch(
                        "latent_triz.a0x_vertical_slice._open_package_parent",
                    ) as package_open:
                        with self.assertRaises(A0XVerticalSliceError):
                            load_vertical_slice(self.root, dossier)
                package_open.assert_not_called()

    def test_load_rejects_symlink_hardlink_or_nonregular_member(self) -> None:
        mutations = ("symlink", "hardlink", "directory")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                if self.package().exists():
                    shutil.rmtree(self.package())
                generate_vertical_slice(self.root, self.request())
                member = self.package() / "protocol.json"
                member.unlink()
                if mutation == "symlink":
                    member.symlink_to("implementation.json")
                elif mutation == "hardlink":
                    os.link(self.package() / "implementation.json", member)
                else:
                    member.mkdir()
                with self.assertRaises(A0XVerticalSliceError):
                    load_vertical_slice(self.root, f"{self.request().output_root}/approval-dossier.json")

    def test_load_rejects_extra_missing_or_duplicate_member(self) -> None:
        mutations = ("extra", "missing", "duplicate")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                if self.package().exists():
                    shutil.rmtree(self.package())
                generate_vertical_slice(self.root, self.request())
                if mutation == "extra":
                    (self.package() / "extra.json").write_bytes(b"{}\n")
                elif mutation == "missing":
                    (self.package() / "protocol.json").unlink()
                else:
                    manifest = (self.package() / "slice-manifest.json").read_bytes()
                    needle = b'"artifact_class":"a0x-vertical-slice-manifest"'
                    replacement = needle + b',"artifact_class":"duplicate"'
                    (self.package() / "slice-manifest.json").write_bytes(manifest.replace(needle, replacement, 1))
                with self.assertRaises(A0XVerticalSliceError):
                    load_vertical_slice(self.root, f"{self.request().output_root}/approval-dossier.json")

    def test_load_rejects_wrong_model_revision(self) -> None:
        generate_vertical_slice(self.root, self.request())
        manifest_path = self.package() / "slice-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["pair"]["revision"] = "c" * 40
        manifest_path.write_bytes(_canonical(manifest))
        with self.assertRaises(A0XVerticalSliceError):
            load_vertical_slice(self.root, f"{self.request().output_root}/approval-dossier.json")

    def test_load_rejects_wrong_freeze_hash_even_with_updated_manifest_hash(self) -> None:
        generate_vertical_slice(self.root, self.request())
        dossier_path = self.package() / "approval-dossier.json"
        dossier = json.loads(dossier_path.read_text())
        dossier["pair_binding"]["leg_freeze_sha256"] = "c" * 64
        dossier_raw = _canonical(dossier)
        dossier_path.write_bytes(dossier_raw)
        manifest_path = self.package() / "slice-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["members"]["approval-dossier.json"]["sha256"] = hashlib.sha256(dossier_raw).hexdigest()
        manifest_path.write_bytes(_canonical(manifest))
        with self.assertRaises(A0XVerticalSliceError):
            load_vertical_slice(self.root, f"{self.request().output_root}/approval-dossier.json")

    def test_load_rejects_manifest_member_hash_mutation(self) -> None:
        generate_vertical_slice(self.root, self.request())
        protocol_path = self.package() / "protocol.json"
        protocol_path.write_bytes(protocol_path.read_bytes() + b" ")
        with self.assertRaises(A0XVerticalSliceError):
            load_vertical_slice(self.root, f"{self.request().output_root}/approval-dossier.json")

    def test_staging_write_failure_removes_only_owned_stage(self) -> None:
        calls = 0

        def fail_second(*args: object, **kwargs: object) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError(errno.EIO, "synthetic write failure")
            original(*args, **kwargs)

        import latent_triz.a0x_vertical_slice as module

        original = module._write_member_at
        with mock.patch.object(module, "_write_member_at", side_effect=fail_second):
            with self.assertRaises(A0XVerticalSliceError) as caught:
                generate_vertical_slice(self.root, self.request())
        self.assertEqual(PUBLICATION_FAILED, caught.exception.code)
        self.assertFalse(self.package().exists())
        self.assertEqual([], list(self.package().parent.glob(".a0x-vertical-slice-*")))

    def test_eexist_publisher_refuses_and_cleans_stage(self) -> None:
        def occupied(_parent_fd: int, _stage_name: str, _destination_name: str) -> None:
            raise FileExistsError(errno.EEXIST, "synthetic occupied")

        with mock.patch("latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at", new=occupied):
            with self.assertRaises(A0XVerticalSliceError) as caught:
                generate_vertical_slice(self.root, self.request())
        self.assertEqual(OUTPUT_EXISTS, caught.exception.code)
        self.assertFalse(self.package().exists())
        self.assertEqual([], list(self.package().parent.glob(".a0x-vertical-slice-*")))

    def test_production_darwin_publisher_uses_required_flags_and_maps_errno(self) -> None:
        class Rename:
            argtypes: list[object] = []
            restype: object = None

            def __init__(self, result: int):
                self.result = result
                self.calls: list[tuple[object, ...]] = []

            def __call__(self, *args: object) -> int:
                self.calls.append(args)
                return self.result

        self.publish_patch.stop()
        try:
            success = Rename(0)
            with mock.patch.object(vertical.sys, "platform", "darwin"):
                with mock.patch.object(
                    vertical.ctypes, "CDLL", return_value=mock.Mock(renameatx_np=success),
                ):
                    vertical._darwin_publish_exclusive_at(17, "stage", "destination")
            self.assertEqual(1, len(success.calls))
            self.assertEqual(17, success.calls[0][0])
            self.assertEqual(b"stage", success.calls[0][1])
            self.assertEqual(17, success.calls[0][2])
            self.assertEqual(b"destination", success.calls[0][3])
            self.assertEqual(vertical.RENAME_EXCL | vertical.RENAME_NOFOLLOW_ANY, success.calls[0][4])

            for observed_errno, expected_code in (
                (errno.EEXIST, OUTPUT_EXISTS),
                (errno.EPERM, PUBLICATION_FAILED),
            ):
                with self.subTest(observed_errno=observed_errno):
                    failure = Rename(-1)
                    library = mock.Mock(renameatx_np=failure)
                    with mock.patch.object(vertical.sys, "platform", "darwin"):
                        with mock.patch.object(vertical.ctypes, "CDLL", return_value=library):
                            with mock.patch.object(vertical.ctypes, "get_errno", return_value=observed_errno):
                                with self.assertRaises(A0XVerticalSliceError) as caught:
                                    vertical._darwin_publish_exclusive_at(17, "stage", "destination")
                    self.assertEqual(expected_code, caught.exception.code)
        finally:
            self.publish_patch.start()

    def test_production_darwin_publisher_refuses_missing_symbol(self) -> None:
        self.publish_patch.stop()
        try:
            with mock.patch.object(vertical.sys, "platform", "darwin"):
                with mock.patch.object(vertical.ctypes, "CDLL", return_value=object()):
                    with self.assertRaises(A0XVerticalSliceError) as caught:
                        vertical._darwin_publish_exclusive_at(17, "stage", "destination")
            self.assertEqual(PUBLICATION_UNSUPPORTED, caught.exception.code)
        finally:
            self.publish_patch.start()

    def test_missing_darwin_primitive_refuses(self) -> None:
        self.publish_patch.stop()
        try:
            with mock.patch("latent_triz.a0x_vertical_slice.sys.platform", "linux"):
                with self.assertRaises(A0XVerticalSliceError) as caught:
                    generate_vertical_slice(self.root, self.request())
            self.assertEqual(PUBLICATION_UNSUPPORTED, caught.exception.code)
            self.assertFalse(self.package().exists())
        finally:
            self.publish_patch.start()

    def test_noop_publisher_refuses_and_cleans_stage(self) -> None:
        with mock.patch("latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at", return_value=None):
            with self.assertRaises(A0XVerticalSliceError) as caught:
                generate_vertical_slice(self.root, self.request())
        self.assertEqual(PUBLICATION_FAILED, caught.exception.code)
        self.assertFalse(self.package().exists())
        self.assertEqual([], list(self.package().parent.glob(".a0x-vertical-slice-*")))

    def test_ancestor_drift_before_publish_refuses(self) -> None:
        def drift(transaction: Any) -> None:
            for parent_fd, name, _identity in transaction.parent.chain:
                if name == "vertical-slices":
                    os.rename(
                        name,
                        "vertical-slices-moved",
                        src_dir_fd=parent_fd,
                        dst_dir_fd=parent_fd,
                    )
                    os.mkdir(name, 0o755, dir_fd=parent_fd)
                    return
            self.fail("vertical-slices ancestor not found")

        with mock.patch("latent_triz.a0x_vertical_slice._before_publish", new=drift):
            with self.assertRaises(A0XVerticalSliceError) as caught:
                generate_vertical_slice(self.root, self.request())
        self.assertEqual(PUBLICATION_FAILED, caught.exception.code)
        self.assertFalse(self.package().exists())

    def test_publisher_rename_then_error_removes_only_owned_destination(self) -> None:
        def rename_then_error(parent_fd: int, stage_name: str, destination_name: str) -> None:
            os.rename(stage_name, destination_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            raise OSError(errno.EIO, "synthetic post-rename error")

        with mock.patch(
            "latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at",
            new=rename_then_error,
        ):
            with self.assertRaises(A0XVerticalSliceError) as caught:
                generate_vertical_slice(self.root, self.request())
        self.assertEqual(PUBLICATION_FAILED, caught.exception.code)
        self.assertFalse(self.package().exists())
        self.assertEqual([], list(self.package().parent.glob(".a0x-vertical-slice-*")))

    def test_final_cleanup_identity_loss_preserves_replacement(self) -> None:
        marker = b"cleanup-replacement"

        def occupied(_parent_fd: int, _stage_name: str, _destination_name: str) -> None:
            raise FileExistsError(errno.EEXIST, "synthetic occupied")

        def replace_before_rmdir(transaction: Any, owned_name: str) -> None:
            parent_fd = transaction.parent.fd
            os.rename(
                owned_name,
                owned_name + "-moved",
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            os.mkdir(owned_name, 0o700, dir_fd=parent_fd)
            replacement_fd = os.open(owned_name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent_fd)
            try:
                descriptor = os.open(
                    "replacement.txt",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=replacement_fd,
                )
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(marker)
            finally:
                os.close(replacement_fd)

        with mock.patch(
            "latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at", new=occupied,
        ):
            with mock.patch(
                "latent_triz.a0x_vertical_slice._before_owned_rmdir", new=replace_before_rmdir,
            ):
                with self.assertRaises(A0XVerticalSliceError) as caught:
                    generate_vertical_slice(self.root, self.request())
        self.assertEqual(PUBLICATION_OWNERSHIP_LOST, caught.exception.code)
        replacement = next(self.package().parent.glob(".a0x-vertical-slice-*/replacement.txt"))
        self.assertEqual(marker, replacement.read_bytes())

    def test_post_publish_ownership_loss_preserves_replacement(self) -> None:
        marker = b"replacement"

        def replace(parent_fd: int, stage_name: str, destination_name: str) -> None:
            os.rename(stage_name, destination_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            destination_fd = os.open(destination_name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent_fd)
            try:
                for name in os.listdir(destination_fd):
                    os.unlink(name, dir_fd=destination_fd)
            finally:
                os.close(destination_fd)
            os.rmdir(destination_name, dir_fd=parent_fd)
            os.mkdir(destination_name, 0o700, dir_fd=parent_fd)
            replacement_fd = os.open(destination_name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent_fd)
            try:
                descriptor = os.open(
                    "replacement.txt",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=replacement_fd,
                )
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(marker)
            finally:
                os.close(replacement_fd)

        with mock.patch("latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at", new=replace):
            with self.assertRaises(A0XVerticalSliceError) as caught:
                generate_vertical_slice(self.root, self.request())
        self.assertEqual(PUBLICATION_OWNERSHIP_LOST, caught.exception.code)
        self.assertEqual(marker, (self.package() / "replacement.txt").read_bytes())

    def test_packages_are_byte_deterministic_in_fresh_roots(self) -> None:
        generate_vertical_slice(self.root, self.request())
        first = {path.name: path.read_bytes() for path in self.package().iterdir()}
        second_root = Path(self.temporary.name) / "second"
        second_root.mkdir()
        _synthetic_repository(second_root)
        generate_vertical_slice(second_root, self.request())
        second_package = second_root / self.request().output_root
        second = {path.name: path.read_bytes() for path in second_package.iterdir()}
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
