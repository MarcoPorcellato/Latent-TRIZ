import hashlib
import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "docs/qualification/a0x-legacy-policy-migration-dossier.json"

LEGACY_OUTER_DIGEST = (
    "sha256:8eb0172c30aac8f9b47f65cebd222ee6615b17e4053a5a16e2be5583f3a10331"
)
LEGACY_RUNTIME_DIGESTS = {
    "python311": (
        "sha256:aa69a8795e20733a516fac99b253cfc26a9f963825ff1fa9ca5638364f7fc943"
    ),
    "python312": (
        "sha256:072e50972a02f2df710bf81620ca058d230f0637bcc16a47ba35562fe1358510"
    ),
}
EXPECTED_IMAGES = {
    "python311": (
        "ghcr.io/marcoporcellato/latent-triz-verify@"
        "sha256:25de19baba5938c80de18c930342ccdcdf3c6759051196c3c713bd3e434d2f0e"
    ),
    "python312": (
        "ghcr.io/marcoporcellato/latent-triz-verify@"
        "sha256:e984457d591121c52517027f49bb55371f68075caace763b8859db136e434dd0"
    ),
}


class A0XPolicyMigrationTests(unittest.TestCase):
    def test_candidate_accepts_only_legacy_plan_without_contract_drift(self) -> None:
        policy = tomllib.loads(
            (ROOT / ".commit-ci-policy-v2.toml").read_text(encoding="utf-8")
        )

        self.assertEqual(policy["schema_version"], "2.0")
        self.assertEqual(policy["project"], "MarcoPorcellato/Latent-TRIZ")
        self.assertEqual(policy["configuration_digest"], LEGACY_OUTER_DIGEST)
        self.assertEqual(policy["max_age_seconds"], 3600)
        self.assertEqual(
            policy["required_checks"],
            [
                {"id": "repository-check-py311", "runtime_id": "python311"},
                {"id": "schema-cross-validate-py311", "runtime_id": "python311"},
                {"id": "repository-check-py312", "runtime_id": "python312"},
                {"id": "schema-cross-validate-py312", "runtime_id": "python312"},
            ],
        )

        runtimes = {runtime["id"]: runtime for runtime in policy["runtimes"]}
        self.assertEqual(set(runtimes), {"python311", "python312"})
        for runtime_id, expected_digest in LEGACY_RUNTIME_DIGESTS.items():
            runtime = runtimes[runtime_id]
            self.assertEqual(runtime["configuration_digest"], expected_digest)
            self.assertEqual(runtime["image_reference"], EXPECTED_IMAGES[runtime_id])
            self.assertEqual(
                runtime["platforms"],
                [
                    {
                        "host_os": "macos",
                        "host_arch": "aarch64",
                        "runtime_kind": "docker_compatible",
                    }
                ],
            )

    def test_public_gate_uses_hosted_repository_checks_without_ccp_receipts(self) -> None:
        workflow = (ROOT / ".github/workflows/merge-policy.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}", workflow)
        self.assertIn("require_repository_check:", workflow)
        self.assertIn("require_python_311:", workflow)
        self.assertIn("name: Repository check (Python 3.12)", workflow)
        self.assertIn("name: Repository check (Python 3.11)", workflow)
        self.assertEqual(workflow.count("python scripts/repository_check.py"), 2)
        self.assertEqual(
            workflow.count("python -m pip install -r requirements-schema.lock"),
            2,
            "each hosted repository lane must install the pinned schema oracle",
        )
        self.assertGreaterEqual(workflow.count("contents: read"), 5)
        self.assertIn("name: Scientific artifact audit", workflow)
        self.assertIn("POLICY_CONTEXT: merge-policy/gate", workflow)
        self.assertNotIn("Exact-head CCP receipt", workflow)
        self.assertNotIn("ccp-evidence/", workflow)
        self.assertNotIn("commit-ci-preflight verify", workflow)
        self.assertNotIn("secrets.", workflow)

    def test_hosted_repository_lanes_fetch_full_history_for_historical_audits(self) -> None:
        workflow = (ROOT / ".github/workflows/merge-policy.yml").read_text(
            encoding="utf-8"
        )
        repository = workflow.split("\n  repository:\n", 1)[1].split(
            "\n  python-311:\n", 1
        )[0]
        python_311 = workflow.split("\n  python-311:\n", 1)[1].split(
            "\n  scientific:\n", 1
        )[0]

        self.assertIn("fetch-depth: 0", repository)
        self.assertIn("fetch-depth: 0", python_311)
        for lane in (repository, python_311):
            self.assertIn(
                "git fetch --no-tags --depth=1 origin "
                "d7a8b5f475480dd0a1f9adcf67df12fd2ae81c1d",
                lane,
            )
            self.assertIn(
                "git fetch --no-tags --depth=1 origin "
                "ab0478331c5bfa9d6b3cb983d5e4550e68f53aa9",
                lane,
            )
            self.assertIn(
                'test "$(git rev-parse '
                'd7a8b5f475480dd0a1f9adcf67df12fd2ae81c1d^{tree})" = '
                '"54c59868802af381f57f830102a01be54410e718"',
                lane,
            )
            self.assertIn(
                'test "$(git rev-parse '
                'ab0478331c5bfa9d6b3cb983d5e4550e68f53aa9^{tree})" = '
                '"ff90ef65cd1ca1c58be620c5241621db5091fa77"',
                lane,
            )

    def test_qualification_dossier_binds_the_old_plan_and_stays_unapproved(self) -> None:
        self.assertTrue(DOSSIER.is_file(), "qualification dossier is missing")
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))
        policy_bytes = (ROOT / ".commit-ci-policy-v2.toml").read_bytes()

        self.assertEqual(dossier["status"], "approval_requested")
        self.assertEqual(
            dossier["trusted_base"]["head"],
            "188eb65b5e249923baddadeba52659f07fcd1609",
        )
        self.assertEqual(
            dossier["candidate_policy"]["sha256"],
            hashlib.sha256(policy_bytes).hexdigest(),
        )
        self.assertEqual(
            dossier["qualification"]["matrix_plan_profile"],
            "matrix-v2-legacy-v1",
        )
        self.assertEqual(
            dossier["qualification"]["expected_plan_digests"],
            {
                "outer": (
                    "sha256:13f4cb39b7e1a8ed31cae64502cc8e4d80d040230d3fb410a6afc3bad3b76178"
                ),
                "python311": (
                    "sha256:eff5b7d55bb0220890dbfb050bb68a1e0fbba8f9a30a69e2f66085354fcc8562"
                ),
                "python312": (
                    "sha256:7afb3e6dd435d9d5a317e4d9d85e80527431044312bbe299e9a70b6ba9e994c8"
                ),
            },
        )
        self.assertEqual(dossier["qualification"]["generation"], 1)
        self.assertEqual(dossier["qualification"]["maximum_runs"], 1)
        self.assertFalse(dossier["authorization"]["granted"])
        self.assertFalse(dossier["execution_state"]["ccp_run_performed"])
        self.assertTrue(dossier["trust_bootstrap"]["candidate_cannot_self_authorize"])

    def test_qualification_plan_is_accepted_by_the_trusted_base(self) -> None:
        dossier = json.loads(DOSSIER.read_text(encoding="utf-8"))

        self.assertEqual(
            dossier["qualification"]["expected_plan_digests"],
            dossier["trusted_base"]["accepted_plan_digests"],
            "the selected qualification plan must be accepted by the trusted base",
        )


if __name__ == "__main__":
    unittest.main()
