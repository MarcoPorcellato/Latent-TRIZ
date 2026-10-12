import copy
import json
from pathlib import Path
import tempfile
import unittest
from urllib.request import Request
from tests.a0x_test_support import synthetic_acquisition_authorization

from latent_triz.exp001_additional_acquisition import (
    MODEL_SPECS,
    _BoundedRedirect,
    AdditionalAcquisitionError,
    acquire_additional,
    build_receipt_from_authorized,
    validate_authorization,
)


ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "experiments/exp001-comparative-reference/additional-model-authorization.json"
NEXT_AUTH_PATH = ROOT / "experiments/exp001-comparative-reference/next-model-authorization.json"


class _Response:
    status = 200
    url = "https://huggingface.co/test"

    def __init__(self, payload: bytes):
        self.payload = payload
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        if not self.payload:
            return b""
        value, self.payload = self.payload[:size], self.payload[size:]
        return value

    def close(self) -> None:
        self.closed = True


class _RangeResponse(_Response):
    status = 206


class _TimeoutResponse(_Response):
    def read(self, size: int = -1) -> bytes:
        if self.payload:
            value, self.payload = self.payload, b""
            return value
        raise TimeoutError("synthetic timeout")


class AdditionalAcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authorization = synthetic_acquisition_authorization()
        cls.next_authorization = synthetic_acquisition_authorization(next_models=True)

    def test_exact_authorization_binds_both_candidates(self):
        for model_id in ("openai-community/gpt2", "HuggingFaceTB/SmolLM2-135M"):
            spec = MODEL_SPECS[model_id]
            validated = validate_authorization(self.authorization, model_id)
            self.assertEqual(validated.revision, spec.revision)
            self.assertEqual(validated.total_declared_bytes, sum(size for _name, size in spec.files))

    def test_approval_requested_and_missing_flag_fail_before_downloader(self):
        refused = copy.deepcopy(self.authorization)
        refused["status"] = "approval_requested"
        for model_id in ("openai-community/gpt2", "HuggingFaceTB/SmolLM2-135M"):
            with self.assertRaises(AdditionalAcquisitionError):
                acquire_additional(model_id, ROOT / MODEL_SPECS[model_id].root_locator, authorization=refused, allow_download=True)
            with self.assertRaises(AdditionalAcquisitionError):
                acquire_additional(model_id, ROOT / MODEL_SPECS[model_id].root_locator, authorization=self.authorization, allow_download=False)

    def test_next_models_are_exactly_bound_and_authorized(self):
        expected = {
            "EleutherAI/gpt-neo-125m": ("21def0189f5705e2521767faed922f1f15e7d7db", 529444041, 8),
            "Qwen/Qwen2.5-0.5B": ("060db6499f32faf8b98477b0a26969ef7d8b9987", 999586188, 7),
        }
        self.assertEqual(self.next_authorization["status"], "authorized")
        for model_id, (revision, total, count) in expected.items():
            frozen = MODEL_SPECS[model_id]
            self.assertEqual(frozen.revision, revision)
            self.assertEqual(frozen.total_declared_bytes, total)
            self.assertEqual(len(frozen.files), count)
            candidate = next(item for item in self.next_authorization["candidates"] if item["model_id"] == model_id)
            self.assertTrue(all(candidate["permissions"].values()))
            validated = validate_authorization(self.next_authorization, model_id)
            self.assertEqual(validated.revision, revision)

    def test_identity_budget_and_permissions_mutations_fail_closed(self):
        for field, value in (("revision", "0" * 40), ("disk_budget_bytes", 1), ("permissions", {})):
            mutated = copy.deepcopy(self.authorization)
            mutated["candidates"][0][field] = value
            with self.assertRaises(AdditionalAcquisitionError):
                validate_authorization(mutated, "openai-community/gpt2")

    def test_huggingface_internal_redirect_is_case_insensitive_and_bound(self):
        spec = MODEL_SPECS["openai-community/gpt2"]
        request = Request(
            "https://huggingface.co/openai-community/gpt2/resolve/" + spec.revision + "/config.json",
            headers={"X-Latent-Triz-Model": spec.model_id, "X-Latent-Triz-Revision": spec.revision},
        )
        redirected = _BoundedRedirect().redirect_request(
            request,
            None,
            307,
            "temporary redirect",
            {},
            "/api/resolve-cache/models/openai-community/gpt2/" + spec.revision + "/config.json?etag=test",
        )
        self.assertIsNotNone(redirected)

    def test_streaming_fake_download_and_receipt(self):
        model_id = "openai-community/gpt2"
        original = MODEL_SPECS[model_id]
        tiny = type(original)(
            model_id=original.model_id,
            revision=original.revision,
            license_id=original.license_id,
            root_locator="artifacts/models/_additional-acquisition-test",
            disk_budget_bytes=64,
            files=(("config.json", 3), ("vocab.json", 2)),
        )
        MODEL_SPECS[model_id] = tiny
        try:
            authorization = copy.deepcopy(self.authorization)
            authorization["candidates"][0]["runtime_root"] = tiny.root_locator
            authorization["candidates"][0]["disk_budget_bytes"] = tiny.disk_budget_bytes
            authorization["candidates"][0]["runtime_files"] = [{"path": n, "size_bytes": s} for n, s in tiny.files]
            with tempfile.TemporaryDirectory(prefix="latent-triz-additional-acquisition-") as workspace:
                workspace_root = Path(workspace)
                root = workspace_root / tiny.root_locator
                responses = iter((_Response(b"abc"), _Response(b"de")))

                def open_response(request, timeout):
                    response = next(responses)
                    response.url = request.full_url
                    return response

                acquire_additional(
                    model_id,
                    root,
                    authorization=authorization,
                    allow_download=True,
                    opener=open_response,
                    repository_root=workspace_root,
                )
                receipt = build_receipt_from_authorized(
                    model_id,
                    root,
                    authorization=authorization,
                    authorization_sha256="a" * 64,
                    repository_root=workspace_root,
                )
                self.assertEqual(receipt["total_bytes"], 5)
                self.assertFalse(receipt["model_loaded"])
        finally:
            MODEL_SPECS[model_id] = original

    def test_streaming_resume_uses_range_and_exact_size(self):
        model_id = "openai-community/gpt2"
        original = MODEL_SPECS[model_id]
        tiny = type(original)(
            model_id=original.model_id,
            revision=original.revision,
            license_id=original.license_id,
            root_locator="artifacts/models/_additional-acquisition-resume-test",
            disk_budget_bytes=64,
            files=(("config.json", 5),),
        )
        MODEL_SPECS[model_id] = tiny
        try:
            authorization = copy.deepcopy(self.authorization)
            authorization["candidates"][0]["runtime_root"] = tiny.root_locator
            authorization["candidates"][0]["disk_budget_bytes"] = tiny.disk_budget_bytes
            authorization["candidates"][0]["runtime_files"] = [{"path": "config.json", "size_bytes": 5}]
            with tempfile.TemporaryDirectory(prefix="latent-triz-additional-resume-") as workspace:
                workspace_root = Path(workspace)
                root = workspace_root / tiny.root_locator
                root.mkdir(parents=True)
                (root / ".config.json.tmp").write_bytes(b"ab")
                requests = []

                def open_response(request, timeout):
                    requests.append(dict(request.header_items()))
                    response = _RangeResponse(b"cde")
                    response.url = request.full_url
                    return response

                acquire_additional(
                    model_id,
                    root,
                    authorization=authorization,
                    allow_download=True,
                    opener=open_response,
                    repository_root=workspace_root,
                )
                self.assertEqual((root / "config.json").read_bytes(), b"abcde")
                self.assertEqual(requests[0]["Range"], "bytes=2-")
        finally:
            MODEL_SPECS[model_id] = original

    def test_timeout_preserves_bounded_partial_for_resume(self):
        model_id = "openai-community/gpt2"
        original = MODEL_SPECS[model_id]
        tiny = type(original)(
            model_id=original.model_id,
            revision=original.revision,
            license_id=original.license_id,
            root_locator="artifacts/models/_additional-acquisition-timeout-test",
            disk_budget_bytes=64,
            files=(("config.json", 5),),
        )
        MODEL_SPECS[model_id] = tiny
        try:
            authorization = copy.deepcopy(self.authorization)
            authorization["candidates"][0]["runtime_root"] = tiny.root_locator
            authorization["candidates"][0]["disk_budget_bytes"] = tiny.disk_budget_bytes
            authorization["candidates"][0]["runtime_files"] = [{"path": "config.json", "size_bytes": 5}]
            with tempfile.TemporaryDirectory(prefix="latent-triz-additional-timeout-") as workspace:
                workspace_root = Path(workspace)
                root = workspace_root / tiny.root_locator

                def open_response(request, timeout):
                    response = _TimeoutResponse(b"ab")
                    response.url = request.full_url
                    return response

                with self.assertRaises(TimeoutError):
                    acquire_additional(
                        model_id,
                        root,
                        authorization=authorization,
                        allow_download=True,
                        opener=open_response,
                        repository_root=workspace_root,
                    )
                self.assertEqual((root / ".config.json.tmp").read_bytes(), b"ab")
                self.assertFalse((root / "config.json").exists())
        finally:
            MODEL_SPECS[model_id] = original


if __name__ == "__main__":
    unittest.main()
