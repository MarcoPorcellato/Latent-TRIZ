"""Target-free regressions for the exact A0X vertical P0 bootstrap."""

from __future__ import annotations

import hashlib
import json
import os
import py_compile
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
    def __init__(self, parent: Path):
        self.root = parent / "repository"
        self.root.mkdir()
        self.import_marker = parent / "repository-imported"
        self.malicious_marker = parent / "malicious-bytecode-executed"
        self.shadow_marker = parent / "path-shadow-executed"
        self.paths = _ledger_paths()
        for index, relative in enumerate(self.paths):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"fixture-{index:03d}\n".encode("ascii"))
        self._write_repository_sources()
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

    def _write_repository_sources(self) -> None:
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
                    return {
                        "artifact_class": "synthetic-a0x-vertical-receipt",
                        "implementation_source_head": request.implementation_source_head,
                        "pair": {"leg": request.leg.value, "model_key": request.model_key},
                        "output_root": request.output_root,
                    }
                """
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
        isolated: bool = True,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        actual_head, actual_tree = self.identity()
        arguments = [str(PYTHON)]
        if isolated:
            arguments.extend(("-I", "-S", "-B"))
        arguments.extend(
            (
                str(self.root / SCRIPT_RELATIVE),
                "--repository-root", str(self.root),
                "--expected-head", actual_head if head is None else head,
                "--expected-tree", actual_tree if tree is None else tree,
                "--expected-python", str(PYTHON),
                "--expected-python-sha256", _sha256(PYTHON),
                "--expected-ledger-sha256", self.ledger_digest() if digest is None else digest,
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

    def fixture(self) -> SyntheticRepository:
        return SyntheticRepository(Path(self.temporary.name))

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
        self.assertEqual("a0", receipt["pair"]["leg"])
        self.assertEqual("smollm2_360m", receipt["pair"]["model_key"])


if __name__ == "__main__":
    unittest.main()
