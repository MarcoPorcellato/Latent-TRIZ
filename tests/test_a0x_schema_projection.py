from __future__ import annotations

import copy
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from jsonschema import Draft202012Validator

from latent_triz.a0x_compatibility import discover_frozen_dossier_paths
from latent_triz.a0x_pair import DenseBound, PairBinding
from latent_triz.a0x_schema_projection import (
    A0X_PAIR_DEFINITION_COUNT,
    A0X_SCHEMA_COUNT,
    canonical_pair_fragment,
    compile_pair_projections,
    discovered_pair_definitions,
    registered_pair_definitions,
)


ROOT = Path(__file__).resolve().parents[1]
_PAIR_FIELDS = {
    "binding_profile", "leg", "leg_freeze_sha256", "model_key", "model_id",
    "revision", "run_id", "output_path", "dense_bound",
}
_DENSE_FIELDS = {
    "leg", "cases", "view_site_count", "endpoint_count", "hidden_width",
    "scalar_bytes", "vector_count", "dense_bytes", "dense_copy_count",
    "atomic_dense_bytes", "index_copy_count", "index_reservation_bytes",
    "payload_allowance_bytes", "total_bytes", "cap_bytes",
}
_OUTPUT_PATH_PATTERN = "^results/a0x/(?:a0|r1)/[A-Za-z0-9][A-Za-z0-9._-]{0,127}/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"


def _walk(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


class A0XSchemaProjectionTests(unittest.TestCase):
    def test_every_pair_definition_is_registered(self) -> None:
        self.assertEqual(discovered_pair_definitions(ROOT), registered_pair_definitions(ROOT))

    def test_baseline_cardinality_is_explicit_and_stable(self) -> None:
        schema_paths = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "schemas").glob("a0x-*.schema.json")
        }
        self.assertEqual(35, A0X_SCHEMA_COUNT)
        self.assertEqual(35, len(schema_paths))
        self.assertTrue({
            "schemas/a0x-hosted-gate-a-capture-request.schema.json",
            "schemas/a0x-hosted-gate-a-capture-transport.schema.json",
        }.issubset(schema_paths))
        self.assertEqual(20, A0X_PAIR_DEFINITION_COUNT)
        self.assertEqual(20, len(discovered_pair_definitions(ROOT)))
        self.assertEqual(20, len(registered_pair_definitions(ROOT)))

    def test_tracked_schemas_equal_compiled_bytes(self) -> None:
        for relative, expected in compile_pair_projections(ROOT).items():
            self.assertEqual(expected, (ROOT / relative).read_bytes(), relative)

    def test_fragment_has_exact_semantic_fields_without_defaults(self) -> None:
        fragment = canonical_pair_fragment()
        self.assertEqual(_PAIR_FIELDS, set(fragment["properties"]))
        self.assertEqual(sorted(_PAIR_FIELDS), fragment["required"])
        self.assertEqual(False, fragment["additionalProperties"])
        self.assertEqual({"const": "a0x-pair-scope-v2"}, fragment["properties"]["binding_profile"])
        self.assertEqual({"enum": ["a0", "r1"]}, fragment["properties"]["leg"])
        self.assertEqual({"type": "string", "pattern": "^[a-f0-9]{64}$"}, fragment["properties"]["leg_freeze_sha256"])
        self.assertEqual({"enum": ["gpt2", "gpt_neo_125m", "qwen2_5_0_5b", "qwen3_0_6b_base", "smollm2_135m", "smollm2_360m"]}, fragment["properties"]["model_key"])
        self.assertEqual({"type": "string", "minLength": 1}, fragment["properties"]["model_id"])
        self.assertEqual({"type": "string", "pattern": "^[a-f0-9]{40}$"}, fragment["properties"]["revision"])
        self.assertEqual({"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"}, fragment["properties"]["run_id"])
        self.assertEqual({"type": "string", "pattern": _OUTPUT_PATH_PATTERN}, fragment["properties"]["output_path"])
        dense = fragment["properties"]["dense_bound"]
        self.assertEqual(_DENSE_FIELDS, set(dense["properties"]))
        self.assertEqual(sorted(_DENSE_FIELDS), sorted(dense["required"]))
        self.assertEqual(False, dense["additionalProperties"])
        self.assertEqual({"enum": ["a0", "r1"]}, dense["properties"]["leg"])
        self.assertEqual({"type": "integer", "const": 48}, dense["properties"]["cases"])
        self.assertEqual({"type": "integer", "minimum": 1}, dense["properties"]["hidden_width"])
        self.assertEqual({"enum": [33_554_432, 4_194_304]}, dense["properties"]["cap_bytes"])
        self.assertFalse(any(key == "default" for key, _ in _walk(fragment)))

    def test_fragment_and_semantic_parser_reject_named_field_divergences(self) -> None:
        from latent_triz.validator import validate
        from tests.a0x_test_support import pair_binding

        fragment = canonical_pair_fragment()
        cases = {
            "binding-profile": lambda value: value.__setitem__("binding_profile", "legacy"),
            "leg": lambda value: value.__setitem__("leg", "other"),
            "freeze-hash": lambda value: value.__setitem__("leg_freeze_sha256", "short"),
            "model-key": lambda value: value.__setitem__("model_key", "unknown"),
            "model-id": lambda value: value.__setitem__("model_id", ""),
            "revision": lambda value: value.__setitem__("revision", "short"),
            "run-id": lambda value: value.__setitem__("run_id", "bad/run"),
            "output-path": lambda value: value.__setitem__("output_path", "results/a0x/a0/gpt2/"),
            "dense-cases": lambda value: value["dense_bound"].__setitem__("cases", 47),
            "dense-hidden-width": lambda value: value["dense_bound"].__setitem__("hidden_width", 0),
            "dense-cap": lambda value: value["dense_bound"].__setitem__("cap_bytes", 1),
            "dense-extra-field": lambda value: value["dense_bound"].__setitem__("surrogate", True),
            "pair-extra-field": lambda value: value.__setitem__("surrogate", True),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label):
                value = pair_binding()
                mutate(value)
                with self.assertRaises(ValueError):
                    PairBinding.from_mapping(value)
                self.assertTrue(validate(value, fragment))
                self.assertTrue(list(Draft202012Validator(fragment).iter_errors(value)))

        parser_only = pair_binding()
        parser_only["dense_bound"]["leg"] = "r1"
        with self.assertRaises(ValueError):
            PairBinding.from_mapping(parser_only)
        self.assertEqual([], validate(parser_only, fragment))
        self.assertEqual([], list(Draft202012Validator(fragment).iter_errors(parser_only)))

    def test_all_registered_definitions_receive_canonical_projection_and_mutation_drift_is_detected(self) -> None:
        compiled = compile_pair_projections(ROOT)
        targets = (
            ("schemas/a0x-statistical-result.schema.json", "a0_pair"),
            ("schemas/a0x-statistical-result.schema.json", "any_pair"),
            ("schemas/a0x-terminal-result.schema.json", "pair"),
            ("schemas/a0x-terminal-result.schema.json", "result_pair"),
        )
        for relative, definition in targets:
            projected = json.loads(compiled[relative])["$defs"][definition]
            self.assertEqual(_OUTPUT_PATH_PATTERN, projected["properties"]["output_path"]["pattern"], (relative, definition))
            self.assertEqual(_PAIR_FIELDS, set(projected["properties"]), (relative, definition))

        from scripts.a0x_compile_pair_schemas import main as compiler_main
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "schemas", root / "schemas")
            self.assertEqual(0, compiler_main(["--write", "--root", str(root)]))
            for relative, definition in targets:
                path = root / relative
                document = json.loads(path.read_text(encoding="utf-8"))
                document["$defs"][definition]["properties"]["output_path"] = {"type": "string", "pattern": "^drift$"}
                path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(1, compiler_main(["--check", "--root", str(root)]), (relative, definition))
                path.write_bytes(compiled[relative])

    def test_write_rejects_unsafe_paths_and_check_mode_writes_nothing(self) -> None:
        from scripts import a0x_compile_pair_schemas as compiler_script

        cases = (
            ("traversal", "schemas/a0x-safe/../../outside.schema.json", "file"),
            ("absolute", "/tmp/a0x-outside.schema.json", "file"),
            ("symlinked-ancestor", "schemas/a0x-safe.schema.json", "schemas-symlink"),
            ("final-symlink", "schemas/a0x-safe.schema.json", "symlink"),
            ("nonregular-target", "schemas/a0x-safe.schema.json", "directory"),
        )
        for label, relative, setup in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                schema_root = root / "schemas"
                schema_root.mkdir()
                outside = root / "outside.schema.json"
                if setup == "schemas-symlink":
                    schema_root.rmdir()
                    external = root / "external"
                    external.mkdir()
                    schema_root.symlink_to(external, target_is_directory=True)
                elif setup == "symlink":
                    (schema_root / "a0x-safe.schema.json").symlink_to(outside)
                elif setup == "directory":
                    (schema_root / "a0x-safe.schema.json").mkdir()
                with mock.patch.object(compiler_script, "compile_pair_projections", return_value={relative: b"{}\n"}):
                    with contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(2, compiler_script.main(["--write", "--root", str(root)]))
                self.assertFalse(outside.exists())

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "schemas").mkdir()
            target = root / "schemas/a0x-safe.schema.json"
            with mock.patch.object(compiler_script, "compile_pair_projections", return_value={"schemas/a0x-safe.schema.json": b"{}\n"}):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(1, compiler_script.main(["--check", "--root", str(root)]))
            self.assertFalse(target.exists())

    def test_write_refuses_visible_schemas_directory_replacement_race(self) -> None:
        from scripts import a0x_compile_pair_schemas as compiler_script

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            schema_root = root / "schemas"
            schema_root.mkdir()
            outside = root / "outside"
            outside.mkdir()
            outside_target = outside / "a0x-safe.schema.json"
            outside_target.write_bytes(b"outside bytes\n")

            def replace_visible_schemas_directory() -> None:
                schema_root.rename(root / "schemas-held")
                schema_root.symlink_to(outside, target_is_directory=True)

            with (
                mock.patch.object(compiler_script, "compile_pair_projections", return_value={"schemas/a0x-safe.schema.json": b"inside bytes\n"}),
                mock.patch.object(compiler_script, "_before_directory_write", side_effect=replace_visible_schemas_directory),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(2, compiler_script.main(["--write", "--root", str(root)]))
            self.assertEqual(b"outside bytes\n", outside_target.read_bytes())

    def test_existing_schema_mutation_corpus_agrees_with_pinned_validator(self) -> None:
        from latent_triz.validator import validate
        from tests.a0x_test_support import artifact, pair_binding, rich_statistical_result
        from tests.test_a0x_schemas import SCHEMA_MUTATIONS, TERMINAL_NESTED_RESULT_MUTATIONS

        schemas = {
            name: json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
            for name in SCHEMA_MUTATIONS
        }
        for name, mutate in SCHEMA_MUTATIONS.items():
            with self.subTest(schema=name):
                invalid = copy.deepcopy(artifact(name))
                mutate(invalid)
                self.assertTrue(validate(invalid, schemas[name]))
                self.assertTrue(list(Draft202012Validator(schemas[name]).iter_errors(invalid)))

        result_schema = schemas["a0x-statistical-result.schema.json"]
        terminal_schema = schemas["a0x-terminal-result.schema.json"]
        result = rich_statistical_result(pair_binding())
        terminal = artifact("a0x-terminal-result.schema.json")
        terminal["statistical_result"] = result
        for label, mutate in TERMINAL_NESTED_RESULT_MUTATIONS:
            with self.subTest(terminal_mutation=label):
                invalid_result = copy.deepcopy(result)
                mutate(invalid_result)
                invalid_terminal = copy.deepcopy(terminal)
                invalid_terminal["statistical_result"] = invalid_result
                self.assertTrue(validate(invalid_result, result_schema))
                self.assertTrue(list(Draft202012Validator(result_schema).iter_errors(invalid_result)))
                self.assertTrue(validate(invalid_terminal, terminal_schema))
                self.assertTrue(list(Draft202012Validator(terminal_schema).iter_errors(invalid_terminal)))

    def test_registry_requires_explicit_overlays_and_compiled_refs_are_local(self) -> None:
        registry = json.loads((ROOT / "schemas/a0x-pair-projections.json").read_text(encoding="utf-8"))
        projections = registry["projections"]
        self.assertEqual(20, len(projections))
        self.assertTrue(all("overlay" in projection for projection in projections))
        self.assertTrue(all(isinstance(projection["overlay"], dict) for projection in projections))
        for relative, payload in compile_pair_projections(ROOT).items():
            document = json.loads(payload)
            for key, value in _walk(document):
                if key == "$ref":
                    self.assertIsInstance(value, str)
                    self.assertTrue(value.startswith("#/"), (relative, value))

    def test_custom_and_pinned_validators_agree_on_generated_schemas_and_real_hosted_projections(self) -> None:
        from latent_triz.validator import validate
        from tests.a0x_test_support import artifact

        compiled = compile_pair_projections(ROOT)
        for relative, payload in compiled.items():
            if relative.endswith(".fragment.json"):
                continue
            schema = json.loads(payload)
            Draft202012Validator.check_schema(schema)
            value = artifact(Path(relative).name)
            self.assertEqual([], validate(value, schema), relative)
            self.assertEqual([], list(Draft202012Validator(schema).iter_errors(value)), relative)
            mutated = copy.deepcopy(value)
            mutated["pair_binding"]["output_path"] = "results/a0x/a0/gpt2/"
            self.assertTrue(validate(mutated, schema), relative)
            self.assertTrue(list(Draft202012Validator(schema).iter_errors(mutated)), relative)

        consumers = (
            ("schemas/a0x-gate-b-authorization.schema.json", "tests/fixtures/a0x/hosted-gate-a/positive/gate-b-authorization.json"),
            ("schemas/a0x-hosted-gate-a-verification-receipt.schema.json", "tests/fixtures/a0x/hosted-gate-a/positive/verification-receipt.json"),
        )
        cases = 0
        for dossier_path in discover_frozen_dossier_paths(ROOT):
            pair_binding = json.loads(dossier_path.read_text(encoding="utf-8"))["pair_binding"]
            for schema_path, template_path in consumers:
                schema = json.loads(compiled[schema_path])
                envelope = json.loads((ROOT / template_path).read_text(encoding="utf-8"))
                envelope["pair_binding"] = copy.deepcopy(pair_binding)
                self.assertEqual([], validate(envelope, schema), (dossier_path, schema_path))
                self.assertEqual([], list(Draft202012Validator(schema).iter_errors(envelope)), (dossier_path, schema_path))
                cases += 1
        self.assertEqual(24, cases)


if __name__ == "__main__":
    unittest.main()
