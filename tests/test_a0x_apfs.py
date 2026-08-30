from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class A0XApfsCloneTests(unittest.TestCase):
    def test_clone_regular_file_proves_independent_exact_bytes(self) -> None:
        from latent_triz.a0x_apfs import clone_regular_file

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.bin"
            destination = root / "destination.bin"
            source.write_bytes(b"runtime bytes")

            def clone_call(source_path: Path, destination_path: Path) -> None:
                destination_path.write_bytes(source_path.read_bytes())

            evidence = clone_regular_file(
                source,
                destination,
                source_root=root,
                destination_root=root,
                platform="darwin",
                clone_call=clone_call,
            )

            self.assertEqual("clonefile", evidence["operation"])
            self.assertEqual(len(b"runtime bytes"), evidence["size_bytes"])
            self.assertEqual(hashlib.sha256(b"runtime bytes").hexdigest(), evidence["sha256"])
            self.assertEqual(1, destination.stat().st_nlink)
            self.assertNotEqual(source.stat().st_ino, destination.stat().st_ino)

    def test_clone_regular_file_refuses_unsupported_platform_without_write(self) -> None:
        from latent_triz.a0x_apfs import A0XClonefileError, clone_regular_file

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.bin"
            destination = root / "destination.bin"
            source.write_bytes(b"runtime bytes")
            with self.assertRaisesRegex(A0XClonefileError, "macOS"):
                clone_regular_file(
                    source,
                    destination,
                    source_root=root,
                    destination_root=root,
                    platform="linux",
                )
            self.assertFalse(os.path.lexists(destination))

    def test_clone_regular_file_refuses_aliases_and_occupied_destination(self) -> None:
        from latent_triz.a0x_apfs import A0XClonefileError, clone_regular_file

        for case in ("source-symlink", "source-hardlink", "parent-symlink", "ancestor-symlink", "occupied"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "source.bin"
                source.write_bytes(b"runtime bytes")
                destination = root / "out/destination.bin"
                destination.parent.mkdir()
                if case == "source-symlink":
                    alias = root / "source-link.bin"
                    alias.symlink_to(source)
                    source = alias
                elif case == "source-hardlink":
                    os.link(source, root / "source-hardlink.bin")
                elif case == "parent-symlink":
                    actual = root / "actual"
                    actual.mkdir()
                    destination.parent.rmdir()
                    destination.parent.symlink_to(actual, target_is_directory=True)
                elif case == "ancestor-symlink":
                    actual = root / "actual"
                    nested = actual / "nested"
                    nested.mkdir(parents=True)
                    destination.parent.rmdir()
                    alias = root / "alias"
                    alias.symlink_to(actual, target_is_directory=True)
                    destination = alias / "nested/destination.bin"
                else:
                    destination.write_bytes(b"preserve")
                clone_call = unittest.mock.Mock(side_effect=AssertionError("clone call reached"))
                with self.assertRaises(A0XClonefileError):
                    clone_regular_file(
                        source,
                        destination,
                        source_root=root,
                        destination_root=root,
                        platform="darwin",
                        clone_call=clone_call,
                    )
                clone_call.assert_not_called()
                if case == "occupied":
                    self.assertEqual(b"preserve", destination.read_bytes())

    def test_clone_regular_file_refuses_post_clone_byte_drift(self) -> None:
        from latent_triz.a0x_apfs import A0XClonefileError, clone_regular_file

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.bin"
            destination = root / "destination.bin"
            source.write_bytes(b"runtime bytes")

            def corrupt_clone(_source: Path, destination_path: Path) -> None:
                destination_path.write_bytes(b"different")

            with self.assertRaisesRegex(A0XClonefileError, "verification"):
                clone_regular_file(
                    source,
                    destination,
                    source_root=root,
                    destination_root=root,
                    platform="darwin",
                    clone_call=corrupt_clone,
                )
            self.assertFalse(os.path.lexists(destination))

    def test_default_clone_uses_darwin_clonefile_boundary(self) -> None:
        from latent_triz.a0x_apfs import clone_regular_file

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.bin"
            destination = root / "destination.bin"
            source.write_bytes(b"runtime bytes")

            def clone_call(source_path: Path, destination_path: Path) -> None:
                destination_path.write_bytes(source_path.read_bytes())

            with patch("latent_triz.a0x_apfs._darwin_clonefile", side_effect=clone_call) as boundary:
                clone_regular_file(
                    source,
                    destination,
                    source_root=root,
                    destination_root=root,
                    platform="darwin",
                )
            boundary.assert_called_once_with(source.resolve(), destination)
