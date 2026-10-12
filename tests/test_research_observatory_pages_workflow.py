from __future__ import annotations

import unittest
from pathlib import Path

import yaml


REPOSITORY = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPOSITORY / ".github/workflows/research-observatory-pages.yml"
EXPECTED_ACTIONS = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python": "a309ff8b426b58ec0e2a45f0f869d46889d02405",
    "actions/setup-node": "49933ea5288caeca8642d1e84afbd3f7d6820020",
    "actions/configure-pages": "983d7736d9b0ae728b81ab479565c72886d7745b",
    "actions/upload-pages-artifact": "7b1f4a764d45c48632c6b24a0339c27f5614fb0b",
    "actions/deploy-pages": "d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e",
}
EXPECTED_ARTIFACT_MEMBERS = {
    "index.html", "style.css", "app.mjs", "site-data.json",
}


class ResearchObservatoryPagesWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        # BaseLoader preserves the GitHub Actions `on` key as a string rather
        # than resolving YAML 1.1's legacy boolean spelling.
        cls.workflow = yaml.load(cls.raw_workflow, Loader=yaml.BaseLoader)

    def test_triggers_read_only_build_for_pull_requests_and_main_pushes(self):
        triggers = self.workflow["on"]
        self.assertIn("pull_request", triggers)
        self.assertEqual(triggers["push"]["branches"], ["main"])
        self.assertEqual(self.workflow["permissions"], {})

        build = self.workflow["jobs"]["build"]
        self.assertEqual(build["permissions"], {"contents": "read"})
        self.assertNotIn("environment", build)
        self.assertIsNone(build.get("needs"))

    def test_deploy_is_main_only_privileged_and_depends_on_successful_build(self):
        deploy = self.workflow["jobs"]["deploy"]
        self.assertEqual(deploy["needs"], "build")
        self.assertEqual(
            deploy["if"], "github.event_name == 'push' && github.ref == 'refs/heads/main'",
        )
        self.assertEqual(
            deploy["permissions"], {"pages": "write", "id-token": "write"},
        )
        self.assertEqual(deploy["environment"]["name"], "github-pages")
        self.assertEqual(
            deploy["environment"]["url"], "${{ steps.deployment.outputs.page_url }}",
        )

    def test_checkout_is_exact_head_and_does_not_persist_credentials(self):
        build = self.workflow["jobs"]["build"]
        checkout = next(
            step["with"] for step in build["steps"]
            if step.get("uses", "").startswith("actions/checkout@")
        )
        self.assertEqual(checkout["ref"], "${{ github.sha }}")
        self.assertEqual(checkout["persist-credentials"], "false")
        self.assertFalse(any(
            step.get("uses", "").startswith("actions/checkout@")
            for step in self.workflow["jobs"]["deploy"]["steps"]
        ))

    def test_actions_use_reviewed_full_commit_references(self):
        found: dict[str, set[str]] = {name: set() for name in EXPECTED_ACTIONS}
        for job in self.workflow["jobs"].values():
            for step in job["steps"]:
                uses = step.get("uses", "")
                if "@" not in uses:
                    continue
                action, ref = uses.rsplit("@", 1)
                if action in found:
                    found[action].add(ref)
                self.assertRegex(ref, r"^[0-9a-f]{40}$", msg=uses)
        for action, expected_sha in EXPECTED_ACTIONS.items():
            with self.subTest(action=action):
                self.assertEqual(found[action], {expected_sha})

    def test_build_runs_locked_policy_tests_site_tests_and_four_file_build(self):
        build = self.workflow["jobs"]["build"]
        steps = build["steps"]
        python_setup = next(s for s in steps if s.get("uses", "").startswith("actions/setup-python@"))
        node_setup = next(s for s in steps if s.get("uses", "").startswith("actions/setup-node@"))
        self.assertEqual(python_setup["with"]["python-version"], "3.11")
        self.assertEqual(node_setup["with"]["node-version"], "22")

        commands = "\n".join(step.get("run", "") for step in steps)
        self.assertIn("pip install --require-hashes -r requirements-schema.lock", commands)
        self.assertIn("tests.test_research_observatory_pages_workflow", commands)
        self.assertIn("scripts.research_observatory.test_site_export", commands)
        self.assertIn("scripts.research_observatory.test_site_build", commands)
        self.assertIn("node --test scripts/research_observatory/site/test_app.mjs", commands)
        self.assertIn("python -m scripts.research_observatory.site_export", commands)
        for member in EXPECTED_ARTIFACT_MEMBERS:
            self.assertIn(member, commands)

    def test_pages_artifact_upload_only_runs_on_main_after_site_build(self):
        build = self.workflow["jobs"]["build"]
        steps = build["steps"]
        configure = next(
            step for step in steps
            if step.get("uses", "").startswith("actions/configure-pages@")
        )
        self.assertEqual(
            configure.get("if"), "github.event_name == 'push' && github.ref == 'refs/heads/main'",
            "Pages configuration must not run on PRs before Pages is enabled",
        )
        upload_index = next(
            index for index, step in enumerate(steps)
            if step.get("uses", "").startswith("actions/upload-pages-artifact@")
        )
        upload = steps[upload_index]
        self.assertEqual(
            upload["if"], "github.event_name == 'push' && github.ref == 'refs/heads/main'",
        )
        self.assertEqual(upload["with"]["path"], "${{ runner.temp }}/research-observatory-site")
        artifact = "\n".join(
            step.get("run", "") for step in steps[:upload_index]
        )
        self.assertIn("index.html", artifact)
        self.assertIn("style.css", artifact)
        self.assertIn("app.mjs", artifact)
        self.assertIn("site-data.json", artifact)

    def test_no_privileged_pull_request_trigger_secrets_or_unpinned_actions(self):
        self.assertNotIn("pull_request_target", self.raw_workflow)
        self.assertNotIn("secrets.", self.raw_workflow)
        self.assertNotIn("GITHUB_TOKEN", self.raw_workflow)
        for job in self.workflow["jobs"].values():
            for step in job["steps"]:
                uses = step.get("uses", "")
                if uses.startswith("actions/"):
                    self.assertRegex(uses, r"^actions/[A-Za-z0-9_-]+@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
