"""Target-free regressions for the exact A0X vertical P0 bootstrap."""

from __future__ import annotations

import hashlib
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_RELATIVE = Path("scripts/a0x_vertical_p0_bootstrap.py")
REVIEW_RELATIVE = Path(
    "docs/qualification/"
    "a0x-vertical-slice-local-review-77dcae52542d21e9bf16e4f17102abf70e68ffc3.md"
)
PYTHON = Path(sys.executable).resolve()
PREEXEC_SOURCE = """\
import hashlib
import hmac
import os
import stat
import sys

MAXIMUM = 64 * 1024 * 1024
CODE = "A0X_VERTICAL_P0_BOOTSTRAP_IDENTITY_MISMATCH"

def refuse():
    print(f"a0x-vertical-p0-preexec: {CODE}", file=sys.stderr)
    raise SystemExit(2)

path = sys.argv[1]
expected_sha256 = sys.argv[2]
if len(expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_sha256):
    refuse()
try:
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= MAXIMUM:
        refuse()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        raw = b"".join(iter(lambda: os.read(descriptor, 1024 * 1024), b""))
        final = os.fstat(descriptor)
    finally:
        os.close(descriptor)
except (AttributeError, OSError):
    refuse()
identity = (before.st_dev, before.st_ino, before.st_size)
if identity != (opened.st_dev, opened.st_ino, opened.st_size) or identity != (final.st_dev, final.st_ino, final.st_size):
    refuse()
if len(raw) != before.st_size or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256):
    refuse()
sys.argv = [
    path,
    *sys.argv[3:],
    "--preexec-bootstrap-device", str(opened.st_dev),
    "--preexec-bootstrap-inode", str(opened.st_ino),
    "--preexec-bootstrap-bytes", str(opened.st_size),
]
globals_for_script = {
    "__name__": "__main__",
    "__file__": path,
    "__package__": None,
    "__cached__": None,
}
exec(compile(raw, path, "exec", dont_inherit=True, optimize=0), globals_for_script, globals_for_script)
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *arguments: str) -> str:
    environment = {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_AUTHOR_NAME": "A0X Test",
        "GIT_AUTHOR_EMAIL": "a0x-test@example.invalid",
        "GIT_COMMITTER_NAME": "A0X Test",
        "GIT_COMMITTER_EMAIL": "a0x-test@example.invalid",
    }
    completed = subprocess.run(
        ("/usr/bin/git", "-C", str(root), *arguments),
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        text=True,
    )
    return completed.stdout.strip()


def _ledger_paths() -> list[str]:
    review = (ROOT / REVIEW_RELATIVE).read_text(encoding="utf-8")
    block = review.split("## Raw P0 package-input ledger", 1)[1]
    lines = block.split("```text\n", 1)[1].split("\n```", 1)[0].splitlines()
    paths = [line.split(" ", 2)[2] for line in lines]
    if len(paths) != 137:
        raise AssertionError(f"unexpected canonical test ledger cardinality: {len(paths)}")
    return paths


class SyntheticRepository:
    def __init__(self, parent: Path, *, cleanup_failure: bool = False):
        self.root = parent / "repository"
        self.root.mkdir()
        self.import_marker = parent / "repository-imported"
        self.malicious_marker = parent / "malicious-bytecode-executed"
        self.shadow_marker = parent / "path-shadow-executed"
        self.bootstrap_replacement_marker = parent / "bootstrap-replacement-executed"
        self.paths = _ledger_paths()
        for index, relative in enumerate(self.paths):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"fixture-{index:03d}\n".encode("ascii"))
        self._write_repository_sources(cleanup_failure=cleanup_failure)
        package = self.root / "src/latent_triz/__init__.py"
        package.write_text("\"\"\"Synthetic package.\"\"\"\n", encoding="utf-8")
        bootstrap = self.root / SCRIPT_RELATIVE
        bootstrap.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / SCRIPT_RELATIVE, bootstrap)
        (self.root / ".gitignore").write_text(
            "__pycache__/\n*.py[cod]\n", encoding="utf-8",
        )
        self._write_ledger_document(self._current_lines())
        _git(self.root, "init", "-q")
        _git(self.root, "add", ".")
        _git(self.root, "commit", "-q", "-m", "synthetic bootstrap fixture")

    def _write_repository_sources(self, *, cleanup_failure: bool) -> None:
        contract = self.root / "src/latent_triz/a0x_contract.py"
        contract.write_text(
            textwrap.dedent(
                f"""\
                from enum import Enum
                from pathlib import Path
                Path({str(self.import_marker)!r}).write_text("imported", encoding="utf-8")
                class Leg(Enum):
                    A0 = "a0"
                """
            ),
            encoding="utf-8",
        )
        vertical = self.root / "src/latent_triz/a0x_vertical_slice.py"
        cleanup_block = ""
        if cleanup_failure:
            cleanup_block = textwrap.indent(
                textwrap.dedent(
                    """\
                    from pathlib import Path
                    import shutil
                    import sys
                    import tempfile
                    cache = Path(sys.pycache_prefix)
                    shutil.rmtree(cache)
                    replacement = Path(tempfile.mkdtemp(prefix="a0x-p0-cleanup-target-"))
                    cache.symlink_to(replacement, target_is_directory=True)
                    """
                ),
                "    ",
            )
        vertical.write_text(
            textwrap.dedent(
                """\
                from dataclasses import dataclass
                @dataclass(frozen=True)
                class VerticalSliceRequest:
                    leg: object
                    model_key: str
                    implementation_source_head: str
                    output_root: str
                def generate_vertical_slice(root, request):
                """
            )
            + cleanup_block
            + textwrap.indent(
                textwrap.dedent(
                    """\
                    return {
                        "artifact_class": "synthetic-a0x-vertical-receipt",
                        "implementation_source_head": request.implementation_source_head,
                        "pair": {"leg": request.leg.value, "model_key": request.model_key},
                        "output_root": request.output_root,
                    }
                    """
                ),
                "    ",
            ),
            encoding="utf-8",
        )

    def _current_lines(self) -> list[str]:
        lines = []
        for relative in sorted(self.paths):
            raw = (self.root / relative).read_bytes()
            lines.append(f"{hashlib.sha256(raw).hexdigest()} {len(raw)} {relative}")
        return lines

    def _write_ledger_document(self, lines: list[str]) -> None:
        document = self.root / REVIEW_RELATIVE
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_text(
            "# Synthetic review\n\n## Raw P0 package-input ledger\n\n```text\n"
            + "\n".join(lines)
            + "\n```\n\n## Exact one-shot P0 command and stop boundary\n",
            encoding="utf-8",
        )

    def commit_all(self, message: str) -> tuple[str, str]:
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", message)
        return self.identity()

    def identity(self) -> tuple[str, str]:
        return _git(self.root, "rev-parse", "HEAD"), _git(
            self.root, "rev-parse", "HEAD^{tree}",
        )

    def ledger_digest(self) -> str:
        payload = ("\n".join(self._current_lines()) + "\n").encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def command(
        self,
        *,
        head: str | None = None,
        tree: str | None = None,
        digest: str | None = None,
        bootstrap_sha256: str | None = None,
        isolated: bool = True,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        actual_head, actual_tree = self.identity()
        arguments = [str(PYTHON)]
        if isolated:
            arguments.extend(("-I", "-S", "-B"))
        expected_bootstrap = (
            _sha256(self.root / SCRIPT_RELATIVE)
            if bootstrap_sha256 is None
            else bootstrap_sha256
        )
        arguments.extend(
            (
                "-c", PREEXEC_SOURCE,
                str(self.root / SCRIPT_RELATIVE),
                expected_bootstrap,
                "--repository-root", str(self.root),
                "--expected-head", actual_head if head is None else head,
                "--expected-tree", actual_tree if tree is None else tree,
                "--expected-python", str(PYTHON),
                "--expected-python-sha256", _sha256(PYTHON),
                "--expected-ledger-sha256", self.ledger_digest() if digest is None else digest,
                "--expected-bootstrap-sha256", expected_bootstrap,
                "--expected-preexec-sha256",
                hashlib.sha256(PREEXEC_SOURCE.encode("utf-8")).hexdigest(),
            )
        )
        child_environment = dict(os.environ)
        if environment:
            child_environment.update(environment)
        return subprocess.run(
            arguments,
            cwd=self.root,
            env=child_environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def add_conflicting_bytecode(self) -> None:
        malicious = self.root.parent / "malicious-a0x-vertical-slice.py"
        malicious.write_text(
            textwrap.dedent(
                f"""\
                from pathlib import Path
                Path({str(self.malicious_marker)!r}).write_text("executed", encoding="utf-8")
                raise RuntimeError("malicious bytecode executed")
                """
            ),
            encoding="utf-8",
        )
        cache = self.root / "src/latent_triz/__pycache__"
        cache.mkdir(parents=True, exist_ok=True)
        target = cache / f"a0x_vertical_slice.{sys.implementation.cache_tag}.pyc"
        py_compile.compile(
            str(malicious),
            cfile=str(target),
            doraise=True,
            invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
        )


class A0XVerticalP0BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="a0x-p0-bootstrap-")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fixture(self, *, cleanup_failure: bool = False) -> SyntheticRepository:
        return SyntheticRepository(
            Path(self.temporary.name), cleanup_failure=cleanup_failure,
        )

    def test_replaced_bootstrap_is_rejected_before_any_replacement_byte_executes(self) -> None:
        fixture = self.fixture()
        expected_sha256 = _sha256(fixture.root / SCRIPT_RELATIVE)
        (fixture.root / SCRIPT_RELATIVE).write_text(
            textwrap.dedent(
                f"""\
                from pathlib import Path
                Path({str(fixture.bootstrap_replacement_marker)!r}).write_text(
                    "executed", encoding="utf-8"
                )
                """
            ),
            encoding="utf-8",
        )
        _git(fixture.root, "update-index", "--assume-unchanged", SCRIPT_RELATIVE.as_posix())
        self.assertEqual("", _git(fixture.root, "status", "--porcelain"))

        completed = fixture.command(bootstrap_sha256=expected_sha256)

        self.assertEqual(2, completed.returncode)
        self.assertIn(
            "A0X_VERTICAL_P0_BOOTSTRAP_IDENTITY_MISMATCH", completed.stderr,
        )
        self.assertFalse(fixture.bootstrap_replacement_marker.exists())

    def test_cleanup_failure_preserves_published_receipt_and_marks_uncertainty(self) -> None:
        fixture = self.fixture(cleanup_failure=True)

        completed = fixture.command(
            bootstrap_sha256=_sha256(fixture.root / SCRIPT_RELATIVE),
        )

        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_PRIVATE_CLEANUP_UNCERTAIN", completed.stderr)
        self.assertTrue(completed.stdout)
        receipt = json.loads(completed.stdout)
        terminal = receipt["p0_authorization_preflight"]["terminal"]
        self.assertEqual("published", terminal["package_publication"])
        self.assertEqual("uncertain", terminal["private_cleanup"])
        self.assertFalse(terminal["retry_permitted"])
        self.assertEqual(
            "shutil.rmtree", terminal["private_cleanup_error"]["operation"],
        )
        self.assertEqual(
            "symlink",
            terminal["private_cleanup_error"]["observed_object"]["object_type"],
        )
        cleanup_path = Path(terminal["private_cleanup_path"])
        cleanup_target = cleanup_path.resolve()
        cleanup_path.unlink()
        shutil.rmtree(cleanup_target)

    def test_authorities_bind_one_full_preexec_through_cleanup_trust_window(self) -> None:
        required = (
            "before pre-execution Python/bootstrap verification and process launch "
            "through terminal receipt emission and private-bootstrap cleanup"
        )
        paths = (
            ROOT / "docs/A0X_VERTICAL_SLICE.md",
            ROOT / REVIEW_RELATIVE,
            ROOT / "artifacts/checkpoints/A0X_VERTICAL_SLICE_RESTART_2026-09-02.md",
        )
        for path in paths:
            with self.subTest(path=path):
                normalized = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
                self.assertIn(required, normalized)

    def test_authorization_commands_embed_the_exact_preexec_source(self) -> None:
        prefix = "python3.13 -I -S -B -c '\n"
        suffix = "\n' /Users/marco1/.codex/worktrees/"
        expected_sha256 = hashlib.sha256(PREEXEC_SOURCE.encode("utf-8")).hexdigest()
        for path in (
            ROOT / REVIEW_RELATIVE,
            ROOT / "artifacts/checkpoints/A0X_VERTICAL_SLICE_RESTART_2026-09-02.md",
        ):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                embedded = text.split(prefix, 1)[1].split(suffix, 1)[0] + "\n"
                self.assertEqual(PREEXEC_SOURCE, embedded)
                self.assertIn(f"--expected-preexec-sha256 {expected_sha256}", text)

    def test_wrong_head_or_tree_refuses_before_repository_import(self) -> None:
        fixture = self.fixture()
        head, tree = fixture.identity()
        for wrong_head, wrong_tree in (("0" * 40, tree), (head, "f" * 40)):
            with self.subTest(head=wrong_head, tree=wrong_tree):
                fixture.import_marker.unlink(missing_ok=True)
                completed = fixture.command(head=wrong_head, tree=wrong_tree)
                self.assertEqual(2, completed.returncode)
                self.assertIn("A0X_VERTICAL_P0_SOURCE_IDENTITY_MISMATCH", completed.stderr)
                self.assertFalse(fixture.import_marker.exists())
                self.assertFalse((fixture.root / "experiments/a0x-six-model/vertical-slices").exists())

    def test_unisolated_runtime_refuses_before_repository_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.command(isolated=False)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_RUNTIME_UNISOLATED", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_path_shadow_cannot_replace_absolute_isolated_python(self) -> None:
        fixture = self.fixture()
        shadow = Path(self.temporary.name) / "shadow"
        shadow.mkdir()
        shadow_python = shadow / "python3"
        shadow_python.write_text(
            f"#!/bin/sh\nprintf executed > {fixture.shadow_marker}\nexit 99\n",
            encoding="utf-8",
        )
        shadow_python.chmod(0o755)
        completed = fixture.command(environment={"PATH": f"{shadow}:/usr/bin:/bin"})
        self.assertEqual(0, completed.returncode, completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual(str(PYTHON), receipt["p0_authorization_preflight"]["python"]["path"])
        self.assertEqual(_sha256(PYTHON), receipt["p0_authorization_preflight"]["python"]["sha256"])
        self.assertFalse(fixture.shadow_marker.exists())
        self.assertTrue(fixture.import_marker.exists())

    def test_valid_conflicting_ignored_bytecode_refuses_before_source_import(self) -> None:
        fixture = self.fixture()
        fixture.add_conflicting_bytecode()
        self.assertEqual("", _git(fixture.root, "status", "--porcelain"))
        completed = fixture.command()
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_BYTECODE_PRESENT", completed.stderr)
        self.assertFalse(fixture.malicious_marker.exists())
        self.assertFalse(fixture.import_marker.exists())

    def test_ledger_cardinality_type_link_and_digest_mismatch_refuse_before_import(self) -> None:
        mutations = ("cardinality", "symlink", "hardlink", "digest")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(
                prefix=f"a0x-p0-{mutation}-",
            ) as directory:
                fixture = SyntheticRepository(Path(directory))
                original_digest = fixture.ledger_digest()
                selected = fixture.root / fixture.paths[0]
                if mutation == "cardinality":
                    fixture._write_ledger_document(fixture._current_lines()[:-1])
                    head, tree = fixture.commit_all("remove ledger member")
                    completed = fixture.command(head=head, tree=tree, digest=original_digest)
                elif mutation == "symlink":
                    replacement = fixture.root / "replacement.txt"
                    replacement.write_bytes(selected.read_bytes())
                    selected.unlink()
                    selected.symlink_to(os.path.relpath(replacement, selected.parent))
                    head, tree = fixture.commit_all("replace ledger member with symlink")
                    completed = fixture.command(head=head, tree=tree, digest=original_digest)
                elif mutation == "hardlink":
                    duplicate = fixture.root / fixture.paths[1]
                    duplicate.write_bytes(selected.read_bytes())
                    fixture._write_ledger_document(fixture._current_lines())
                    fixture.commit_all("align ledger member bytes")
                    selected.unlink()
                    os.link(duplicate, selected)
                    self.assertEqual("", _git(fixture.root, "status", "--porcelain"))
                    completed = fixture.command(digest=fixture.ledger_digest())
                else:
                    selected.write_bytes(b"changed tracked input\n")
                    head, tree = fixture.commit_all("change ledger input")
                    completed = fixture.command(head=head, tree=tree, digest=original_digest)
                self.assertEqual(2, completed.returncode)
                self.assertIn("A0X_VERTICAL_P0_LEDGER_MISMATCH", completed.stderr)
                self.assertFalse(fixture.import_marker.exists())

    def test_success_receipt_binds_source_launcher_python_and_ledger(self) -> None:
        fixture = self.fixture()
        head, tree = fixture.identity()
        completed = fixture.command()
        self.assertEqual(0, completed.returncode, completed.stderr)
        receipt = json.loads(completed.stdout)
        preflight = receipt["p0_authorization_preflight"]
        self.assertEqual(head, preflight["source"]["head"])
        self.assertEqual(tree, preflight["source"]["tree"])
        self.assertEqual(137, preflight["input_ledger"]["count"])
        self.assertEqual(fixture.ledger_digest(), preflight["input_ledger"]["sha256"])
        self.assertEqual(SCRIPT_RELATIVE.as_posix(), preflight["launcher"]["path"])
        self.assertEqual(
            _sha256(fixture.root / SCRIPT_RELATIVE), preflight["launcher"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(PREEXEC_SOURCE.encode("utf-8")).hexdigest(),
            preflight["preexec_verifier"]["source_sha256"],
        )
        self.assertEqual(
            preflight["launcher"]["bytes"],
            preflight["preexec_verifier"]["bootstrap_descriptor"]["bytes"],
        )
        self.assertEqual("published", preflight["terminal"]["package_publication"])
        self.assertEqual("complete", preflight["terminal"]["private_cleanup"])
        self.assertFalse(preflight["terminal"]["retry_permitted"])
        self.assertEqual("a0", receipt["pair"]["leg"])
        self.assertEqual("smollm2_360m", receipt["pair"]["model_key"])


if __name__ == "__main__":
    unittest.main()
