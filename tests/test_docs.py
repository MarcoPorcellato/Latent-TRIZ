from __future__ import annotations

import io
import json
import os
import posixpath
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from datetime import date
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.docs import (
    A0X_N3_DEFERRED_LINK_PATHS,
    A0X_N3_EXCLUDED_SENSITIVE_LINK_PATHS,
    A0X_N3_PROTECTED_LINK_PATHS,
    audit_docs,
    load_profile,
)


class DocsAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[1]

    def test_docs_audit_passes_for_fixture_profile(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/conformant/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/conformant", date.fromisoformat("2026-08-13"))
        self.assertEqual(issues, [])

    def test_cli_docs_audit_no_findings_returns_zero(self) -> None:
        from latent_triz.cli import main

        err = io.StringIO()
        with redirect_stderr(err):
            code = main(
                [
                    "docs-audit",
                    "--profile",
                    str(self.repo / "tests/fixtures/docs/conformant/profile.toml"),
                    "--root",
                    str(self.repo / "tests/fixtures/docs/conformant"),
                    "--as-of-date",
                    "2026-08-13",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue(), "")

    def test_load_profile_rejects_absolute_entry_point(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            profile = Path(workdir) / "profile.toml"
            profile.write_text(
                """
[okf]
required_fields = ["type", "title", "description", "status", "last_verified"]
max_verification_age_days = 180
entry_points = ["/docs/README.md"]
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "absolute entry point"):
                load_profile(str(profile))

    def test_load_profile_rejects_root_escape_entry_point(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            profile = Path(workdir) / "profile.toml"
            profile.write_text(
                """
[okf]
required_fields = ["type", "title", "description", "status", "last_verified"]
max_verification_age_days = 180
entry_points = ["../docs/README.md"]
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "entry point escapes docs root"):
                load_profile(str(profile))

    def test_load_profile_rejects_non_markdown_entry_point(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            profile = Path(workdir) / "profile.toml"
            profile.write_text(
                """
[okf]
required_fields = ["type", "title", "description", "status", "last_verified"]
max_verification_age_days = 180
entry_points = ["docs/README.txt"]
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "must be Markdown"):
                load_profile(str(profile))

    def test_load_profile_rejects_zero_or_negative_max_verification_age(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            profile = Path(workdir) / "profile.toml"
            profile.write_text(
                """
[okf]
required_fields = ["type", "title", "description", "status", "last_verified"]
max_verification_age_days = 0
entry_points = ["docs/README.md"]
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "greater than 0"):
                load_profile(str(profile))

    def test_load_profile_accepts_legacy_max_age_days(self) -> None:
        legacy_path = self.repo / "tests/fixtures/docs/fail_stale_last_verified/profile.toml"
        profile = load_profile(str(legacy_path))
        self.assertEqual(profile.max_age_days, 1)

    def test_missing_frontmatter_is_reported(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/fail_missing_frontmatter/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/fail_missing_frontmatter", date.fromisoformat("2026-08-13"))
        self.assertTrue(any(issue.code == "DOCS_MISSING_FRONTMATTER" for issue in issues))

    def test_unterminated_frontmatter_is_reported(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/fail_unterminated_frontmatter/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/fail_unterminated_frontmatter", date.fromisoformat("2026-08-13"))
        self.assertTrue(any(issue.code == "DOCS_UNTERMINATED_FRONTMATTER" for issue in issues))

    def test_missing_required_field_is_reported(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/fail_missing_required_field/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/fail_missing_required_field", date.fromisoformat("2026-08-13"))
        self.assertTrue(any(issue.code == "DOCS_MISSING_FIELD" for issue in issues))

    def test_invalid_last_verified_is_reported(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/fail_invalid_last_verified/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/fail_invalid_last_verified", date.fromisoformat("2026-08-13"))
        self.assertTrue(any(issue.code == "DOCS_LAST_VERIFIED_FORMAT" for issue in issues))

    def test_future_last_verified_is_reported(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/fail_future_last_verified/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/fail_future_last_verified", date.fromisoformat("2026-08-13"))
        self.assertTrue(any(issue.code == "DOCS_LAST_VERIFIED_FUTURE" for issue in issues))

    def test_stale_last_verified_is_reported(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/fail_stale_last_verified/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/fail_stale_last_verified", date.fromisoformat("2026-08-13"))
        self.assertTrue(any(issue.code == "DOCS_LAST_VERIFIED_STALE" for issue in issues))

    def test_missing_link_target_is_reported(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/fail_missing_target/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/fail_missing_target", date.fromisoformat("2026-08-13"))
        self.assertTrue(any(issue.code == "DOCS_LINK_TARGET_MISSING" for issue in issues))

    def test_missing_anchor_is_reported(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/fail_missing_anchor/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/fail_missing_anchor", date.fromisoformat("2026-08-13"))
        self.assertTrue(any(issue.code == "DOCS_LINK_ANCHOR_MISSING" for issue in issues))

    def test_root_escape_is_reported(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/fail_root_escape/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/fail_root_escape", date.fromisoformat("2026-08-13"))
        self.assertTrue(any(issue.code == "DOCS_ROOT_ESCAPE" for issue in issues))

    def test_protected_and_sensitive_links_defer_before_filesystem_access(self) -> None:
        manifest_path = self.repo / "docs/qualification/a0x-target-free-schema-profile-v1-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        protected = {item[0] for item in manifest["instance_dispositions"]["deferred_protected"]}
        sensitive = {
            item["instance"]
            for item in manifest["legacy_pairs"]
            if item.get("disposition") == "excluded_sensitive_role_unverified"
        }
        self.assertEqual(len(protected), 4)
        self.assertEqual(len(sensitive), 14)
        blocked = protected | sensitive
        self.assertEqual(A0X_N3_PROTECTED_LINK_PATHS, protected)
        self.assertEqual(A0X_N3_EXCLUDED_SENSITIVE_LINK_PATHS, sensitive)
        self.assertEqual(A0X_N3_DEFERRED_LINK_PATHS, blocked)

        with tempfile.TemporaryDirectory() as workdir:
            root = Path(workdir)
            docs_dir = root / "docs"
            docs_dir.mkdir()
            profile_path = root / "profile.toml"
            profile_path.write_text(
                '[okf]\nrequired_fields = ["type", "title", "description", "status", "last_verified"]\n'
                'max_verification_age_days = 180\nentry_points = ["docs/index.md"]\n',
                encoding="utf-8",
            )
            links = [
                f"[protected-{index}]({posixpath.relpath(target, 'docs')})"
                for index, target in enumerate(sorted(blocked))
            ]
            synthetic_target = root / "data/a0/sealed-targets/targets.jsonl"
            synthetic_target.parent.mkdir(parents=True)
            synthetic_target.write_text("# Synthetic heading\n", encoding="utf-8")
            (docs_dir / "sealed-alias").symlink_to(synthetic_target.parent, target_is_directory=True)
            links.extend(
                [
                    "[encoded](%2E%2E%2Fdata%2Fa0%2Fsealed-targets%2Ftargets.jsonl)",
                    "[case-variant](../DATA/A0/SEALED-TARGETS/TARGETS.JSONL)",
                    "[symlink-alias](sealed-alias/targets.jsonl#synthetic-heading)",
                ]
            )
            (docs_dir / "index.md").write_text(
                "---\ntype: entry\ntitle: Synthetic\ndescription: Synthetic fixture\n"
                "status: canonical\nlast_verified: 2026-10-01\n---\n\n"
                + "\n".join(links)
                + "\n",
                encoding="utf-8",
            )
            profile = load_profile(str(profile_path))
            root_abs = posixpath.normpath(os.path.abspath(os.fspath(root)))
            blocked_folded = {path.casefold() for path in blocked}
            attempted: list[str] = []
            fd_paths: dict[int, str] = {}

            def relative_path(value: object, dir_fd: int | None = None) -> str | None:
                raw = os.fsdecode(os.fspath(value))
                if dir_fd is not None and not posixpath.isabs(raw):
                    parent = fd_paths.get(dir_fd)
                    if parent is None:
                        return None
                    candidate = posixpath.normpath(posixpath.join(parent, raw))
                else:
                    absolute = posixpath.normpath(os.path.abspath(raw))
                    candidate = posixpath.relpath(absolute, root_abs)
                if candidate == ".":
                    return ""
                if candidate == ".." or candidate.startswith("../"):
                    return None
                return candidate.replace("\\", "/").casefold()

            def reject_blocked(value: object, dir_fd: int | None = None) -> str | None:
                candidate = relative_path(value, dir_fd)
                if candidate and any(
                    candidate == blocked or candidate.startswith(blocked + "/")
                    for blocked in blocked_folded
                ):
                    attempted.append(candidate or "")
                    raise AssertionError(f"filesystem access reached deferred path: {candidate}")
                return candidate

            path_originals = {
                name: getattr(Path, name)
                for name in ("resolve", "is_file", "exists", "stat", "lstat", "open", "read_text", "read_bytes")
            }
            for name, original in path_originals.items():
                def guarded_path(path: Path, *args: object, _original=original, **kwargs: object):
                    reject_blocked(path)
                    return _original(path, *args, **kwargs)

                patcher = patch.object(Path, name, guarded_path)
                patcher.start()
                self.addCleanup(patcher.stop)

            os_originals = {name: getattr(os, name) for name in ("stat", "lstat", "open", "close")}

            def guarded_stat(name: str):
                original = os_originals[name]

                def wrapped(path: object, *args: object, **kwargs: object):
                    reject_blocked(path, kwargs.get("dir_fd"))
                    return original(path, *args, **kwargs)

                return wrapped

            def guarded_open(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None):
                candidate = reject_blocked(path, dir_fd)
                result = os_originals["open"](path, flags, mode, dir_fd=dir_fd)
                if candidate is not None and flags & getattr(os, "O_DIRECTORY", 0):
                    fd_paths[result] = candidate
                return result

            def guarded_close(fd: int) -> None:
                fd_paths.pop(fd, None)
                os_originals["close"](fd)

            with patch.object(os, "stat", guarded_stat("stat")), patch.object(
                os, "lstat", guarded_stat("lstat")
            ), patch.object(os, "open", guarded_open), patch.object(os, "close", guarded_close):
                issues = audit_docs(profile, root, date.fromisoformat("2026-10-01"))

        deferred = [issue for issue in issues if issue.code == "DOCS_LINK_TARGET_DEFERRED_PROTECTED"]
        excluded = [issue for issue in issues if issue.code == "DOCS_LINK_TARGET_EXCLUDED_SENSITIVE_UNVERIFIED"]
        unverified = [issue for issue in issues if issue.code == "DOCS_LINK_TARGET_UNVERIFIED"]
        self.assertEqual(len(deferred), len(protected) + 2, repr(issues))
        self.assertEqual(len(excluded), len(sensitive), repr(issues))
        self.assertEqual(len(unverified), 1, repr(issues))
        self.assertTrue(all("deferred_protected / UNVERIFIED" in issue.message for issue in deferred))
        self.assertTrue(all("excluded_sensitive_role_unverified / UNVERIFIED" in issue.message for issue in excluded))
        self.assertIn("UNVERIFIED", unverified[0].message)
        self.assertEqual(attempted, [])

    def test_public_file_link_without_anchor_is_checked_without_reading_target(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            root = Path(workdir)
            docs_dir = root / "docs"
            docs_dir.mkdir()
            (docs_dir / "index.md").write_text(
                "---\ntype: entry\ntitle: Synthetic\ndescription: Fixture\n"
                "status: canonical\nlast_verified: 2026-10-01\n---\n\n"
                "[guide](guide.md)\n",
                encoding="utf-8",
            )
            (docs_dir / "guide.md").write_text("# Synthetic guide\n", encoding="utf-8")
            profile_path = root / "profile.toml"
            profile_path.write_text(
                '[okf]\nrequired_fields = ["type", "title", "description", "status", "last_verified"]\n'
                'max_verification_age_days = 180\nentry_points = ["docs/index.md"]\n',
                encoding="utf-8",
            )

            profile = load_profile(str(profile_path))
            issues = audit_docs(profile, root, date.fromisoformat("2026-10-01"))

        self.assertEqual(issues, [])

    def test_missing_entry_point_directory_counts_missing_entry(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            root = Path(workdir)
            entry_dir = root / "docs"
            entry_dir.mkdir()
            (entry_dir / "README.md").mkdir()
            profile_path = root / "profile.toml"
            profile_path.write_text(
                """
[okf]
required_fields = ["type", "title", "description", "status", "last_verified"]
max_verification_age_days = 10
entry_points = ["docs/README.md"]
""",
                encoding="utf-8",
            )
            profile = load_profile(str(profile_path))
            issues = audit_docs(profile, root, date.fromisoformat("2026-08-13"))
            self.assertTrue(any(issue.code == "PROFILE_MISSING_ENTRY" for issue in issues))

    def test_duplicate_canonical_type_is_reported(self) -> None:
        profile = load_profile(str(self.repo / "tests/fixtures/docs/fail_duplicate_type/profile.toml"))
        issues = audit_docs(profile, self.repo / "tests/fixtures/docs/fail_duplicate_type", date.fromisoformat("2026-08-13"))
        self.assertTrue(any(issue.code == "DOCS_DUP_CANONICAL_TYPE" for issue in issues))

    def test_cli_command_returns_findings_and_formats_codes(self) -> None:
        from latent_triz.cli import main

        errors = io.StringIO()
        with redirect_stderr(errors):
            code = main(
                [
                    "docs-audit",
                    "--profile",
                    str(self.repo / "tests/fixtures/docs/fail_missing_frontmatter/profile.toml"),
                    "--root",
                    str(self.repo / "tests/fixtures/docs/fail_missing_frontmatter"),
                    "--as-of-date",
                    "2026-08-13",
                ]
            )
        self.assertEqual(code, 1)
        out = errors.getvalue()
        self.assertIn("DOCS_MISSING_FRONTMATTER", out)

    def test_cli_docs_audit_broken_profile_is_clean_error(self) -> None:
        from latent_triz.cli import main

        with tempfile.TemporaryDirectory() as workdir:
            profile = Path(workdir) / "profile.toml"
            profile.write_text("{ required_fields = [ ", encoding="utf-8")
            errors = io.StringIO()
            with redirect_stderr(errors):
                code = main(
                    [
                        "docs-audit",
                        "--profile",
                        str(profile),
                        "--root",
                        str(self.repo),
                        "--as-of-date",
                        "2026-08-13",
                    ]
                )
            err = errors.getvalue()
            self.assertEqual(code, 1)
            self.assertIn("invalid profile", err)
            self.assertNotIn("Traceback", err)

    def test_cli_docs_audit_missing_profile_is_clean_error(self) -> None:
        from latent_triz.cli import main

        missing = self.repo / "tests/fixtures/docs/does-not-exist.toml"
        errors = io.StringIO()
        with redirect_stderr(errors):
            code = main(
                [
                    "docs-audit",
                    "--profile",
                    str(missing),
                    "--root",
                    str(self.repo),
                    "--as-of-date",
                    "2026-08-13",
                ]
            )
        err = errors.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("invalid profile", err)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
