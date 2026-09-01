from __future__ import annotations

import ast
import inspect
import json
import unittest
from pathlib import Path

from latent_triz.a0x_schema_projection import (
    discovered_pair_definitions,
    registered_pair_definitions,
)


ROOT = Path(__file__).resolve().parents[1]


def _module_tree(name: str) -> ast.Module:
    return ast.parse((ROOT / "src/latent_triz" / name).read_text(encoding="utf-8"))


def _imported_modules(name: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(_module_tree(name)):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.removeprefix("."))
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def _imports_module(imports: set[str], target: str) -> bool:
    return any(module == target or module.endswith(f".{target}") for module in imports)


class A0XArchitectureTests(unittest.TestCase):
    def test_every_pair_binding_projection_is_registered(self) -> None:
        self.assertEqual(
            discovered_pair_definitions(ROOT),
            registered_pair_definitions(ROOT),
        )

    def test_pair_fixture_helper_uses_canonical_output_derivation(self) -> None:
        from tests import a0x_test_support

        source = inspect.getsource(a0x_test_support.pair_binding)
        self.assertIn("derive_pair_output_path", source)
        self.assertNotIn("results/a0x/", source)

    def test_hosted_positive_fixtures_equal_canonical_builder_output(self) -> None:
        from latent_triz.a0x_hosted_gate_a import canonical_json_bytes
        from tests.a0x_test_support import hosted_gate_a_fixture_documents

        authorization, receipt = hosted_gate_a_fixture_documents()
        fixtures = (
            ("gate-b-authorization.json", authorization),
            ("verification-receipt.json", receipt),
        )
        fixture_root = ROOT / "tests/fixtures/a0x/hosted-gate-a/positive"
        for filename, document in fixtures:
            with self.subTest(filename=filename):
                self.assertEqual(
                    canonical_json_bytes(document),
                    canonical_json_bytes(json.loads((fixture_root / filename).read_text(encoding="utf-8"))),
                )

    def test_runner_and_material_adapter_use_canonical_reducer(self) -> None:
        for module in ("a0x_runner.py", "a0x_material_runtime.py"):
            with self.subTest(module=module):
                source = (ROOT / "src/latent_triz" / module).read_text(encoding="utf-8")
                self.assertIn("from .a0x_execution import AttemptEvent, AttemptState, reduce_attempt", source)
                self.assertIn("reduce_attempt(", source)

    def test_pair_domain_imports_no_io_adapter(self) -> None:
        prohibited = {
            "a0x_ccp_executor", "a0x_freeze", "a0x_hosted_gate_a", "a0x_material_runtime",
            "a0x_production_adapter", "a0x_runner", "a0x_wheelhouse",
        }
        self.assertFalse(prohibited & _imported_modules("a0x_pair.py"))

    def test_contract_and_material_contract_have_no_import_cycle(self) -> None:
        contract_imports = _imported_modules("a0x_contract.py")
        material_imports = _imported_modules("a0x_material_contract.py")
        self.assertFalse(
            _imports_module(contract_imports, "a0x_material_contract")
            and _imports_module(material_imports, "a0x_contract"),
        )

    def test_repository_check_runs_compatibility_oracle(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("check: a0x-compatibility-check", makefile)


if __name__ == "__main__":
    unittest.main()
