from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path


def _canonical(value: dict[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class A0XOfflineWheelhouseTests(unittest.TestCase):
    def _fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, object]]:
        temporary = tempfile.TemporaryDirectory()
        base = Path(temporary.name)
        root = base / "wheelhouse"
        root.mkdir()
        filename = "example_pkg-1.2.3-py3-none-any.whl"
        raw = b"synthetic wheel bytes"
        (root / filename).write_bytes(raw)
        manifest: dict[str, object] = {
            "profile": "a0x-offline-wheelhouse-v1",
            "python_major_minor": [3, 11],
            "accepted_tags": ["py3-none-any"],
            "wheels": [{
                "distribution": "example-pkg",
                "version": "1.2.3",
                "filename": filename,
                "tag": "py3-none-any",
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }],
        }
        return temporary, root, manifest

    def test_verifies_exact_canonical_offline_wheelhouse(self) -> None:
        from latent_triz.a0x_wheelhouse import verify_offline_wheelhouse

        temporary, root, manifest = self._fixture()
        self.addCleanup(temporary.cleanup)
        raw = _canonical(manifest)
        evidence = verify_offline_wheelhouse(root, raw)
        self.assertEqual("verified", evidence["status"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), evidence["manifest_sha256"])
        self.assertEqual(1, evidence["wheel_count"])
        self.assertEqual(len(b"synthetic wheel bytes"), evidence["total_size_bytes"])

    def test_rejects_noncanonical_manifest_without_touching_wheels(self) -> None:
        from latent_triz.a0x_wheelhouse import A0XWheelhouseError, verify_offline_wheelhouse

        temporary, root, manifest = self._fixture()
        self.addCleanup(temporary.cleanup)
        original = (root / manifest["wheels"][0]["filename"]).read_bytes()  # type: ignore[index]
        with self.assertRaisesRegex(A0XWheelhouseError, "canonical"):
            verify_offline_wheelhouse(root, json.dumps(manifest, indent=2).encode())
        self.assertEqual(original, (root / manifest["wheels"][0]["filename"]).read_bytes())  # type: ignore[index]

    def test_rejects_missing_extra_and_changed_wheels(self) -> None:
        from latent_triz.a0x_wheelhouse import A0XWheelhouseError, verify_offline_wheelhouse

        for case in ("missing", "extra", "changed"):
            with self.subTest(case=case):
                temporary, root, manifest = self._fixture()
                self.addCleanup(temporary.cleanup)
                wheel = root / manifest["wheels"][0]["filename"]  # type: ignore[index]
                if case == "missing":
                    wheel.unlink()
                elif case == "extra":
                    (root / "extra-1.0-py3-none-any.whl").write_bytes(b"extra")
                else:
                    wheel.write_bytes(b"changed")
                with self.assertRaises(A0XWheelhouseError):
                    verify_offline_wheelhouse(root, _canonical(manifest))

    def test_rejects_symlink_and_hardlink_wheels(self) -> None:
        from latent_triz.a0x_wheelhouse import A0XWheelhouseError, verify_offline_wheelhouse

        for case in ("symlink", "hardlink"):
            with self.subTest(case=case):
                temporary, root, manifest = self._fixture()
                self.addCleanup(temporary.cleanup)
                wheel = root / manifest["wheels"][0]["filename"]  # type: ignore[index]
                if case == "symlink":
                    source = root.parent / "source.bin"
                    wheel.rename(source)
                    wheel.symlink_to(source)
                else:
                    os.link(wheel, root.parent / "alias.bin")
                with self.assertRaises(A0XWheelhouseError):
                    verify_offline_wheelhouse(root, _canonical(manifest))

    def test_rejects_filename_distribution_version_or_tag_mismatch(self) -> None:
        from latent_triz.a0x_wheelhouse import A0XWheelhouseError, verify_offline_wheelhouse

        for field, value in (
            ("distribution", "other"),
            ("version", "9.9"),
            ("tag", "cp311-cp311-macosx_11_0_arm64"),
        ):
            with self.subTest(field=field):
                temporary, root, manifest = self._fixture()
                self.addCleanup(temporary.cleanup)
                manifest["wheels"][0][field] = value  # type: ignore[index]
                with self.assertRaises(A0XWheelhouseError):
                    verify_offline_wheelhouse(root, _canonical(manifest))

    def test_rejects_duplicate_distribution_and_wrong_python_contract(self) -> None:
        from latent_triz.a0x_wheelhouse import A0XWheelhouseError, verify_offline_wheelhouse

        temporary, root, manifest = self._fixture()
        self.addCleanup(temporary.cleanup)
        first = dict(manifest["wheels"][0])  # type: ignore[index]
        second_name = "example_pkg-1.2.3-py3-none-any-copy.whl"
        (root / second_name).write_bytes(b"second")
        first.update({
            "filename": second_name,
            "size_bytes": len(b"second"),
            "sha256": hashlib.sha256(b"second").hexdigest(),
        })
        manifest["wheels"].append(first)  # type: ignore[union-attr]
        with self.assertRaises(A0XWheelhouseError):
            verify_offline_wheelhouse(root, _canonical(manifest))

        temporary2, root2, manifest2 = self._fixture()
        self.addCleanup(temporary2.cleanup)
        manifest2["python_major_minor"] = [3, 12]
        with self.assertRaisesRegex(A0XWheelhouseError, "Python 3.11"):
            verify_offline_wheelhouse(root2, _canonical(manifest2))
