"""Synthetic fail-closed tests for Hosted Gate A capture."""

from __future__ import annotations

import hashlib
import io
import json
import base64
import os
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

HEAD = "a" * 40
TREE = "b" * 40


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _zip_member(name: str, payload: bytes) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        member = zipfile.ZipInfo(name)
        member.compress_type = zipfile.ZIP_DEFLATED
        member.external_attr = 0o100644 << 16
        archive.writestr(member, payload)
    return stream.getvalue()


def _encrypted_flag_zip(name: str, payload: bytes) -> bytes:
    raw = bytearray(_zip_member(name, payload))
    for signature, offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        index = raw.index(signature)
        raw[index + offset] |= 0x01
    return bytes(raw)


def _typed_zip(name: str, payload: bytes, mode: int) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        member = zipfile.ZipInfo(name)
        member.create_system = 3
        member.external_attr = mode << 16
        archive.writestr(member, payload)
    return stream.getvalue()


class HostedCaptureTest(unittest.TestCase):
    def _request(self, output_root: Path) -> dict[str, object]:
        return {
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "source_head": HEAD,
            "source_tree": TREE,
            "run_id": 123,
            "run_attempt": 1,
            "artifact_id": 456,
            "artifact_name": "a0x-hosted-gate-a-evidence",
            "archive_sha256": "",
            "archive_size_bytes": 0,
            "manifest_sha256": "",
            "expires_at": "2026-09-02T12:00:00Z",
            "output_root": str(output_root),
        }

    def _manifest(self, *, head: str = HEAD, tree: str = TREE, run_id: int = 123) -> bytes:
        from latent_triz.a0x_hosted_gate_a import LANE_IDS, build_lane_receipt, build_manifest

        commands = {
            "a0x-no-model": ("make", "a0x-no-model-verify"),
            "a0x-synthetic": ("make", "a0x-synthetic-verify"),
            "documentation-audit": ("make", "docs-audit"),
            "repository-python311": ("python", "scripts/repository_check.py"),
            "repository-python312": ("python", "scripts/repository_check.py"),
            "schema-cross-validation-python311": ("python", "scripts/schema_cross_validate.py"),
            "schema-cross-validation-python312": ("python", "scripts/schema_cross_validate.py"),
        }
        outputs = [
            base64.urlsafe_b64encode(build_lane_receipt(lane, head, tree, commands[lane], "PASS")).rstrip(b"=").decode("ascii")
            for lane in LANE_IDS
        ]
        return build_manifest(
            repository="MarcoPorcellato/Latent-TRIZ", source_head=head, source_tree=tree,
            workflow_sha256="c" * 64, run_id=run_id, run_attempt=1,
            requirements_lock_sha256="d" * 64, action_manifest_sha256="e" * 64,
            lane_manifest_sha256="f" * 64, encoded_lane_outputs=outputs,
        )

    def _inputs(self, root: Path) -> tuple[dict[str, object], dict[str, object], Path, bytes, bytes]:
        manifest = self._manifest()
        archive = _zip_member("a0x-hosted-gate-a-evidence.json", manifest)
        archive_path = root / "artifact.zip"
        archive_path.write_bytes(archive)
        request = self._request(root / "capture")
        request.update({
            "archive_sha256": hashlib.sha256(archive).hexdigest(),
            "archive_size_bytes": len(archive),
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        })
        transport = {
            "artifact_id": 456, "run_id": 123, "run_attempt": 1, "head_sha": HEAD,
            "archive_digest": "sha256:" + hashlib.sha256(archive).hexdigest(), "archive_size_bytes": len(archive),
            "created_at": "2026-09-01T11:00:00Z", "expires_at": "2026-09-02T12:00:00Z",
            "captured_at": "2026-09-01T12:00:00Z",
        }
        return request, transport, archive_path, b'{"synthetic":"bundle"}\n', b'{"synthetic":"trusted-root"}\n'

    def test_capture_publishes_exact_four_file_set_with_exclusive_injected_publisher(self) -> None:
        """Removing archive/member/cross-binding publication must fail this capture."""
        from latent_triz.a0x_hosted_capture import CaptureRequest, CaptureTransport, capture_hosted_gate_a

        manifest = self._manifest()
        archive = _zip_member("a0x-hosted-gate-a-evidence.json", manifest)
        bundle = b'{"synthetic":"bundle"}\n'
        trusted_root = b'{"synthetic":"trusted-root"}\n'
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            archive_path = root / "artifact.zip"
            archive_path.write_bytes(archive)
            request = self._request(root / "capture")
            request["archive_sha256"] = hashlib.sha256(archive).hexdigest()
            request["archive_size_bytes"] = len(archive)
            request["manifest_sha256"] = hashlib.sha256(manifest).hexdigest()
            transport = {
                "artifact_id": 456,
                "run_id": 123,
                "run_attempt": 1,
                "head_sha": HEAD,
                "archive_digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
                "archive_size_bytes": len(archive),
                "created_at": "2026-09-01T11:00:00Z",
                "expires_at": "2026-09-02T12:00:00Z",
                "captured_at": "2026-09-01T12:00:00Z",
            }
            calls: list[tuple[Path, Path]] = []

            def publish(stage: Path, destination: Path) -> None:
                calls.append((stage, destination))
                stage.rename(destination)

            result = capture_hosted_gate_a(
                CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), archive_path,
                bundle, trusted_root, publish=publish,
            )

            self.assertEqual(root / "capture", result)
            self.assertEqual([(root / "capture").name], [destination.name for _, destination in calls])
            self.assertEqual(
                {
                    "hosted-gate-a-evidence.json",
                    "hosted-gate-a-attestation.bundle.jsonl",
                    "github-trusted-root.jsonl",
                    "hosted-gate-a-transport.json",
                },
                {path.name for path in result.iterdir()},
            )
            self.assertEqual(manifest, (result / "hosted-gate-a-evidence.json").read_bytes())
            self.assertEqual(bundle, (result / "hosted-gate-a-attestation.bundle.jsonl").read_bytes())
            self.assertEqual(trusted_root, (result / "github-trusted-root.jsonl").read_bytes())
            self.assertEqual(
                "a0x-hosted-gate-a-transport",
                json.loads((result / "hosted-gate-a-transport.json").read_bytes())["artifact_class"],
            )
            transport_schema = json.loads((ROOT / "schemas/a0x-hosted-gate-a-capture-transport.schema.json").read_text())
            self.assertEqual([], __import__("latent_triz.validator", fromlist=["validate"]).validate(
                json.loads((result / "hosted-gate-a-transport.json").read_bytes()), transport_schema,
            ))

    def test_request_refuses_nonabsolute_output_and_metadata_drift(self) -> None:
        """Removing exact request shape or absolute output validation must fail capture admission."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CAPTURE_INVALID, CaptureRequest

        with TemporaryDirectory() as temporary:
            request = self._request(Path(temporary).resolve() / "capture")
            request["output_root"] = "relative/capture"
            with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
                CaptureRequest.from_mapping(request)
            request = self._request(Path(temporary).resolve() / "capture")
            request["unknown"] = "must-refuse"
            with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
                CaptureRequest.from_mapping(request)

    def test_pinned_cli_revalidation_refuses_version_path_or_bytes_drift(self) -> None:
        """Removing any per-call executable binding check would admit a substituted CLI."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, PIN_INVALID, PinnedGitHubCLI, revalidate_pinned_cli

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            executable = root / "synthetic-gh"
            executable.write_bytes(b"synthetic pinned bytes\n")
            pinned = PinnedGitHubCLI(executable, hashlib.sha256(executable.read_bytes()).hexdigest())
            for path, version in (
                (executable, b"wrong version\n"),
                (root / "other-gh", b"gh version 2.97.0 (2026-07-31)\n"),
            ):
                with self.subTest(path=path, version=version):
                    with self.assertRaisesRegex(A0XHostedCaptureError, PIN_INVALID):
                        revalidate_pinned_cli(pinned, path, version)
            executable.write_bytes(b"substituted bytes\n")
            with self.assertRaisesRegex(A0XHostedCaptureError, PIN_INVALID):
                revalidate_pinned_cli(pinned, executable, b"gh version 2.97.0 (2026-07-31)\n")

    def test_capture_refuses_extra_traversal_encrypted_or_nonregular_zip_members(self) -> None:
        """Removing ZIP member gates would permit a path, encryption, or nonregular archive attack."""
        from latent_triz.a0x_hosted_capture import ARCHIVE_INVALID, A0XHostedCaptureError, CaptureRequest, CaptureTransport, capture_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            request, transport, archive_path, bundle, trusted = self._inputs(root)
            manifest = self._manifest()
            for label, members in (
                ("extra", [("a0x-hosted-gate-a-evidence.json", manifest), ("extra", b"x")]),
                ("traversal", [("../a0x-hosted-gate-a-evidence.json", manifest)]),
            ):
                stream = io.BytesIO()
                with zipfile.ZipFile(stream, "w") as archive:
                    for name, raw in members:
                        info = zipfile.ZipInfo(name)
                        info.external_attr = 0o100644 << 16
                        archive.writestr(info, raw)
                raw_archive = stream.getvalue()
                archive_path.write_bytes(raw_archive)
                request["archive_sha256"] = hashlib.sha256(raw_archive).hexdigest()
                request["archive_size_bytes"] = len(raw_archive)
                transport["archive_digest"] = "sha256:" + request["archive_sha256"]
                transport["archive_size_bytes"] = len(raw_archive)
                with self.subTest(label=label), self.assertRaisesRegex(A0XHostedCaptureError, ARCHIVE_INVALID):
                    capture_hosted_gate_a(CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), archive_path, bundle, trusted, publish=lambda _stage, _destination: None)
                self.assertFalse((root / "capture").exists())

    def test_capture_refuses_transport_cross_binding_without_output(self) -> None:
        """Removing request-to-transport identity equality would publish mismatched evidence."""
        from latent_triz.a0x_hosted_capture import BINDING_MISMATCH, A0XHostedCaptureError, CaptureRequest, CaptureTransport, capture_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            request, transport, archive_path, bundle, trusted = self._inputs(root)
            transport["head_sha"] = "c" * 40
            with self.assertRaisesRegex(A0XHostedCaptureError, BINDING_MISMATCH):
                capture_hosted_gate_a(CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), archive_path, bundle, trusted, publish=lambda _stage, _destination: None)
            self.assertFalse((root / "capture").exists())

    def test_failed_publication_removes_owned_stage_and_never_creates_final_output(self) -> None:
        """Removing transaction cleanup or exclusive publication would leave partial evidence behind."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CaptureRequest, CaptureTransport, PUBLICATION_FAILED, capture_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            request, transport, archive_path, bundle, trusted = self._inputs(root)
            with self.assertRaisesRegex(A0XHostedCaptureError, PUBLICATION_FAILED):
                capture_hosted_gate_a(
                    CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), archive_path, bundle, trusted,
                    publish=lambda _stage, _destination: (_ for _ in ()).throw(OSError("synthetic publish failure")),
                )
            self.assertFalse((root / "capture").exists())
            self.assertEqual([], list(root.glob(".a0x-hosted-capture-*")))

    def test_capture_schemas_reject_request_path_and_transport_attempt_drift(self) -> None:
        """Removing schema bounds would admit an unbound local path or rerun transport."""
        from latent_triz.validator import validate

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            request, transport, _archive, _bundle, _trusted = self._inputs(root)
            schemas = {
                name: json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
                for name in (
                    "a0x-hosted-gate-a-capture-request.schema.json",
                    "a0x-hosted-gate-a-capture-transport.schema.json",
                )
            }
            self.assertEqual([], validate(request, schemas["a0x-hosted-gate-a-capture-request.schema.json"]))
            from latent_triz.a0x_hosted_capture import CaptureTransport
            self.assertEqual([], validate(
                json.loads(CaptureTransport.from_mapping(transport).as_document()),
                schemas["a0x-hosted-gate-a-capture-transport.schema.json"],
            ))
            request["output_root"] = "relative/capture"
            self.assertTrue(validate(request, schemas["a0x-hosted-gate-a-capture-request.schema.json"]))
            transport["run_attempt"] = 2
            with self.assertRaises(ValueError):
                CaptureTransport.from_mapping(transport)

    def test_capture_refuses_archive_links_and_existing_output(self) -> None:
        """Removing regular independent archive or exclusive output checks would permit replay or replacement."""
        from latent_triz.a0x_hosted_capture import ARCHIVE_INVALID, OUTPUT_EXISTS, A0XHostedCaptureError, CaptureRequest, CaptureTransport, capture_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            request, transport, archive_path, bundle, trusted = self._inputs(root)
            linked = root / "archive-link.zip"
            os.link(archive_path, linked)
            with self.assertRaisesRegex(A0XHostedCaptureError, ARCHIVE_INVALID):
                capture_hosted_gate_a(CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), linked, bundle, trusted, publish=lambda _stage, _destination: None)
            output = root / "capture"
            output.mkdir()
            with self.assertRaisesRegex(A0XHostedCaptureError, OUTPUT_EXISTS):
                capture_hosted_gate_a(CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), archive_path, bundle, trusted, publish=lambda _stage, _destination: None)

    def test_capture_refuses_manifest_and_each_transport_binding_drift(self) -> None:
        """Removing any request/manifest/transport equality would publish mixed-run bytes."""
        from latent_triz.a0x_hosted_capture import BINDING_MISMATCH, A0XHostedCaptureError, CaptureRequest, CaptureTransport, capture_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            request, transport, archive_path, bundle, trusted = self._inputs(root)
            drifted_manifest = self._manifest(tree="c" * 40)
            drifted_archive = _zip_member("a0x-hosted-gate-a-evidence.json", drifted_manifest)
            archive_path.write_bytes(drifted_archive)
            request.update({
                "archive_sha256": hashlib.sha256(drifted_archive).hexdigest(),
                "archive_size_bytes": len(drifted_archive),
                "manifest_sha256": hashlib.sha256(drifted_manifest).hexdigest(),
            })
            transport.update({
                "archive_digest": "sha256:" + request["archive_sha256"],
                "archive_size_bytes": request["archive_size_bytes"],
            })
            with self.assertRaisesRegex(A0XHostedCaptureError, BINDING_MISMATCH):
                capture_hosted_gate_a(CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), archive_path, bundle, trusted, publish=lambda _stage, _destination: None)
            request, transport, archive_path, bundle, trusted = self._inputs(root)
            for field, value in (
                ("artifact_id", 457), ("run_id", 124), ("head_sha", "c" * 40),
                ("archive_digest", "sha256:" + "d" * 64), ("archive_size_bytes", transport["archive_size_bytes"] + 1),
                ("expires_at", "2026-09-03T12:00:00Z"),
            ):
                drifted = dict(transport)
                drifted[field] = value
                with self.subTest(field=field), self.assertRaisesRegex(A0XHostedCaptureError, BINDING_MISMATCH):
                    capture_hosted_gate_a(CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(drifted), archive_path, bundle, trusted, publish=lambda _stage, _destination: None)
                self.assertFalse((root / "capture").exists())

    def test_capture_refuses_nested_symlink_and_non_directory_ancestors(self) -> None:
        """Removing full ancestor checks would redirect a capture below a symlinked path component."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CAPTURE_INVALID, CaptureRequest, CaptureTransport, capture_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            request, transport, archive, bundle, trusted = self._inputs(root)
            redirect_target = root / "redirect-target"
            (redirect_target / "inner").mkdir(parents=True)
            (root / "link").symlink_to(redirect_target, target_is_directory=True)
            request["output_root"] = str(root / "link" / "inner" / "capture")
            with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
                capture_hosted_gate_a(CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), archive, bundle, trusted, publish=lambda _stage, _destination: None)
            request, transport, archive, bundle, trusted = self._inputs(root)
            (root / "blocked").write_bytes(b"not a directory")
            request["output_root"] = str(root / "blocked" / "inner" / "capture")
            with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
                capture_hosted_gate_a(CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), archive, bundle, trusted, publish=lambda _stage, _destination: None)

    def test_noop_or_invalid_publisher_cleans_owned_stage(self) -> None:
        """Removing post-publication cleanup would leave synthetic staged evidence after a bad publisher."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CaptureRequest, CaptureTransport, PUBLICATION_FAILED, capture_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for publisher in (lambda _stage, _destination: None, lambda stage, _destination: (stage / "unexpected").write_bytes(b"x")):
                with self.subTest(publisher=publisher):
                    request, transport, archive, bundle, trusted = self._inputs(root)
                    with self.assertRaisesRegex(A0XHostedCaptureError, PUBLICATION_FAILED):
                        capture_hosted_gate_a(CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), archive, bundle, trusted, publish=publisher)
                    self.assertEqual([], list(root.glob(".a0x-hosted-capture-*")))
                    self.assertFalse((root / "capture").exists())

    def test_request_transport_and_schemas_refuse_semantically_invalid_utc_timestamps(self) -> None:
        """Replacing semantic UTC parsing with regex-only checks would admit impossible dates and times."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CaptureRequest, CaptureTransport
        from latent_triz.validator import validate

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            request, transport, _archive, _bundle, _trusted = self._inputs(root)
            request["expires_at"] = "2026-99-99T99:99:99Z"
            transport["created_at"] = "2026-02-30T12:00:00Z"
            with self.assertRaises(A0XHostedCaptureError):
                CaptureRequest.from_mapping(request)
            with self.assertRaises(A0XHostedCaptureError):
                CaptureTransport.from_mapping(transport)
            request_schema = json.loads((ROOT / "schemas/a0x-hosted-gate-a-capture-request.schema.json").read_text())
            self.assertTrue(validate(request, request_schema))

    def test_capture_refuses_actual_encrypted_directory_symlink_and_nonregular_zip_members(self) -> None:
        """Removing ZIP flags/type validation would accept an encrypted or nonregular archive member."""
        from latent_triz.a0x_hosted_capture import ARCHIVE_INVALID, A0XHostedCaptureError, CaptureRequest, CaptureTransport, capture_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            request, transport, archive, bundle, trusted = self._inputs(root)
            manifest = self._manifest()
            fixtures = {
                "encrypted": _encrypted_flag_zip("a0x-hosted-gate-a-evidence.json", manifest),
                "directory": _typed_zip("a0x-hosted-gate-a-evidence.json/", b"", 0o40755),
                "symlink": _typed_zip("a0x-hosted-gate-a-evidence.json", b"target", 0o120777),
                "fifo": _typed_zip("a0x-hosted-gate-a-evidence.json", b"", 0o010644),
            }
            for label, raw in fixtures.items():
                archive.write_bytes(raw)
                request.update({"archive_sha256": hashlib.sha256(raw).hexdigest(), "archive_size_bytes": len(raw)})
                transport.update({"archive_digest": "sha256:" + request["archive_sha256"], "archive_size_bytes": len(raw)})
                with self.subTest(label=label), self.assertRaisesRegex(A0XHostedCaptureError, ARCHIVE_INVALID):
                    capture_hosted_gate_a(CaptureRequest.from_mapping(request), CaptureTransport.from_mapping(transport), archive, bundle, trusted, publish=lambda _stage, _destination: None)
