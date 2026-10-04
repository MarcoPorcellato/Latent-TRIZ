"""Bounded, isolated engineering tests; no production corpus or scientific attempt.

Run only with the coordinator-recorded interpreter under -I -S -B. The baseline
mode preserves an owned synthetic oracle; subsequent modes consume its exact
bytes, never historical artifacts.
"""
from __future__ import annotations
import copy
import hashlib
import json
import linecache
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import unicodedata
from fractions import Fraction

ROOT = Path(__file__).absolute().parents[1]
SOURCES = {
    "__init__.py": "db06d3f6e4698ca55d12b13a7064e0b2d4bac9c966b5bdd930d3d3faf861d34c",
    "a0_power.py": "baaa74257823234a7a5973231dae855d586e88dd3b30a7184aceb82f4aa05b41",
    "a0_shortcuts.py": "f1cd33fd28e0f758d0d8dd34ea21e35e958b00c1491a13f0c3a32bb8411b5aa4",
    "a0_calibration.py": "6106de793e3ecaedb9ebff2470e7d190f3cdd03fc58aab5277e7e66e8b0bae3f",
}
SELECTION = {
    "method_id": "a0x-shortcut-calibration-method-v2.0.0",
    "leg": "A0", "model": "HuggingFaceTB/SmolLM2-360M",
    "revision": "f8027fd0eaeea54caa13c31d31b9fdc459c38b49",
}
CONTROLS = (
    "bag_of_words_baselines", "character_ngram_baselines",
    "length_and_punctuation_baselines", "style_and_template_baselines",
    "provenance_classifiers", "problem_only_label_prediction",
    "leave_one_domain_out_surface_evaluation", "generic_action_taxonomy_controls",
    "generic_transformation_taxonomy_controls", "adjacent_principle_proxy_controls",
    "random_label_controls", "random_partition_controls",
    "duplicate_and_near_duplicate_detection", "family_leakage_detection",
)
LABELS = ["inversion_like", "segmentation_like"]
MODE = os.environ.get("A0X_SYNTHETIC_MODE", "tests")
EXPECTED = dict(SOURCES)
if MODE != "baseline":
    supplied = json.loads(os.environ.get("A0X_WRITER_HASHES", "{}"))
    if supplied:
        if set(supplied) != {"a0_shortcuts.py", "a0_calibration.py"}:
            raise RuntimeError("unexpected source binding")
        EXPECTED.update(supplied)

def read_independent(path, expected=None):
    """Read admitted bytes through no-follow directory/file descriptors."""
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise RuntimeError("noncanonical admission")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        leaf = path.name
        leaf_fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            before = os.fstat(leaf_fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise RuntimeError("source is not independent regular")
            chunks = []
            while chunk := os.read(leaf_fd, 65536):
                chunks.append(chunk)
            data = b"".join(chunks)
            after = os.fstat(leaf_fd)
            current = os.stat(leaf, dir_fd=fd, follow_symlinks=False)
            keys = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
            if keys(before) != keys(after) or keys(before) != keys(current):
                raise RuntimeError("admitted identity changed")
            if expected and hashlib.sha256(data).hexdigest() != expected:
                raise RuntimeError("source hash mismatch")
            return data
        finally:
            os.close(leaf_fd)
    finally:
        os.close(fd)

# Admit the whole fixed name set before copying any admitted content.
if set(EXPECTED) != set(SOURCES):
    raise RuntimeError("snapshot closure changed")
source_bytes = {name: read_independent(ROOT / "src/latent_triz" / name, digest)
                for name, digest in EXPECTED.items()}
SESSION = Path(tempfile.mkdtemp(prefix="a0x-d1d7-synthetic-", dir="/private/tmp"))
SESSION_ID = (SESSION.stat().st_dev, SESSION.stat().st_ino)
PACKAGE = SESSION / "package/latent_triz"
PACKAGE.mkdir(parents=True)
def write_new(path, data):
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
for name, data in source_bytes.items():
    write_new(PACKAGE / name, data)
    assert read_independent(PACKAGE / name, EXPECTED[name]) == data
sys.path.insert(0, str(PACKAGE.parent))
# Traceback formatting must not reopen the live driver after admission.
driver_text = read_independent(Path(__file__).absolute()).decode("utf-8")
linecache.cache[str(Path(__file__).absolute())] = (
    len(driver_text), None, driver_text.splitlines(keepends=True), str(Path(__file__).absolute()))
FORBIDDEN_ROOT = str(ROOT)
def access_guard(event, args):
    if event in {"socket.__new__", "subprocess.Popen", "os.system"}:
        raise AssertionError("external execution/network forbidden")
    if event in {"open", "os.listdir", "os.scandir", "os.chdir"} and args:
        value = args[0]
        if isinstance(value, (str, bytes, os.PathLike)):
            text = os.fsdecode(value)
            if text == FORBIDDEN_ROOT or text.startswith(FORBIDDEN_ROOT + os.sep):
                raise AssertionError("original-root access after admission")
            if Path(text).name == "inert-sealed-never-open.jsonl":
                raise AssertionError("synthetic sealed locator accessed")
sys.addaudithook(access_guard)
from latent_triz import a0_shortcuts as shortcuts
from latent_triz import a0_calibration as calibration
for module in (shortcuts, calibration):
    assert str(module.__file__).startswith(str(PACKAGE) + os.sep)

def stable(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
def fixture():
    """Independently constructed values, not any production freeze."""
    cases, targets = [], []
    for domain in range(6):
        for family in range(2):
            for variant, label in enumerate(LABELS):
                identity = f"c{len(cases)}"
                cases.append({
                    "case_id": identity, "problem_family_id": f"d{domain}f{family}",
                    "solution_variant_id": str(variant), "domain": f"d{domain}",
                    "split": "calibration", "problem": f"Unique payload {identity}",
                    "initial_state": "neutral", "desired_improvement": "neutral",
                    "worsening_consequence": "neutral", "transformation": "neutral",
                    "resulting_state": "neutral", "solution": "neutral", "constraints": [],
                })
                targets.append({
                    "case_id": identity, "split": "calibration", "operator_proxy_family": label,
                    "provenance": {"template_id": "template", "generator_id": "generator"},
                })
    protocol = {
        "protocol_id": "independent-synthetic-d1d7", "protocol_status": "draft",
        "neutral_domains": [f"d{i}" for i in range(6)],
        "preregistered_layers": [0], "token_sites": ["synthetic-site"],
        "predeclared_calibration_rule": {
            "candidate_families_per_domain": [1], "permutation_budgets": [19],
            "target_power": .8, "maximum_false_positive_rate": .05, "target_effect_size": .5,
        },
        "shortcut_evaluation": {
            "macro_f1_threshold": .65, "margin_over_majority": .1,
            "a0_controls": list(CONTROLS),
        },
    }
    return cases, targets, protocol

def mechanics(cases):
    views = {
        "bow": {"kind": "word_unigrams", "fields": ["initial_state"]},
        "char": {"kind": "char_3_5_grams", "fields": ["initial_state"]},
        "length": {"kind": "length_and_punctuation", "fields": ["initial_state"]},
        "style": {"kind": "categorical", "fields": ["template_id", "generator_id"]},
        "problem": {"kind": "word_unigrams", "fields": ["problem"]},
        "taxonomy": {"kind": "keyword_counts", "fields": ["transformation"],
                     "lexicon": {"inversion_like": ["reverse"], "segmentation_like": ["split"]}},
    }
    ordinary = dict(zip(CONTROLS[:10],
                       [["bow"], ["char"], ["length"], ["style"], ["style"], ["problem"],
                        ["bow"], ["taxonomy"], ["taxonomy"], ["taxonomy"]]))
    all_views = sorted({view for values in ordinary.values() for view in values})
    ordinary["random_label_controls"] = all_views
    ordinary["random_partition_controls"] = all_views
    units = [{"id": f"u{i}", "fold": "fold-0", "domain": f"d{i}",
              "train_ids": [r["case_id"] for r in cases if r["domain"] != f"d{i}"],
              "test_ids": [r["case_id"] for r in cases if r["domain"] == f"d{i}"]}
             for i in range(6)]
    contract = {
        "schema": "a0x-shortcut-mechanics-engineering-v1", "classes": list(LABELS),
        "views": views, "control_views": ordinary, "units": units,
        "replicas": [{"id": "replica-0", "seed": 0}],
        "randomizer": "python-mt19937-shuffle-v1", "python_version": sys.version.split()[0],
        "partition_train_families": {f"d{i}": 1 for i in range(6)},
        "partition_assignments": {"replica-0": {
            f"d{i}": {"train_families": [f"d{i}f0"], "test_families": [f"d{i}f1"]}
            for i in range(6)}},
        "algorithm": "nearest-centroid-squared-euclidean-v1",
        "numerics": "binary64-features-fraction-metrics-v1", "tie_break": "utf8-lexicographic",
        "payload_stages": [{"id": "raw", "fields": ["problem"]}],
        "payload_encoding": "length-prefixed-utf8-v1",
        "normalization": "utf8-nfc-lf-v1", "unicode_version": unicodedata.unidata_version,
        "boundaries": [["train", "test"]],
    }
    return {"contract": contract, "sha256": hashlib.sha256(stable(contract)).hexdigest()}

def rebind(evidence):
    evidence["sha256"] = hashlib.sha256(stable(evidence["contract"])).hexdigest()
    return evidence

def materialize(cases, targets, protocol):
    root = Path(tempfile.mkdtemp(prefix="fixture-", dir=SESSION))
    corpus = root / "corpus"
    corpus.mkdir()
    pp = root / "protocol.json"
    write_new(pp, stable(protocol))
    files = {}
    for name, rows in [("cases", cases), ("calibration-targets", targets)]:
        data = b"".join(stable(row) + b"\n" for row in rows)
        write_new(corpus / f"{name}.jsonl", data)
        files["cases_jsonl" if name == "cases" else "calibration_targets_jsonl"] = {
            "path": f"{name}.jsonl", "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    files["sealed_targets_jsonl"] = {
        "path": "inert-sealed-never-open.jsonl", "sha256": "0" * 64, "size": 0}
    manifest = {
        "protocol_id": protocol["protocol_id"], "protocol_hash": hashlib.sha256(stable(protocol)).hexdigest(),
        "empirical": True, "scientific_status": "exploratory", "evidence_eligible": False,
        "expert_validated": False, "claim_ids": [], "files": files,
    }
    write_new(corpus / "manifest.json", stable(manifest))
    return pp, corpus, root / "output"

def audit(cases, targets, protocol, evidence):
    pp, corpus, _ = materialize(cases, targets, protocol)
    try:
        return shortcuts.audit_a0_shortcuts(corpus / "cases.jsonl", corpus / "calibration-targets.jsonl",
            pp, method_selection=SELECTION, mechanical_evidence=evidence)
    except TypeError as exc:
        raise AssertionError(f"missing prospective real audit behavior: {exc}") from exc

def consumer(cases, targets, protocol, evidence):
    pp, corpus, output = materialize(cases, targets, protocol)
    try:
        result = calibration.run_a0_calibration(pp, corpus, output,
            method_selection=SELECTION, mechanical_evidence=evidence)
    except TypeError as exc:
        raise AssertionError(f"missing prospective real consumer behavior: {exc}") from exc
    return result, output

def baseline():
    cases, targets, protocol = fixture()
    pp, corpus, output = materialize(cases, targets, protocol)
    result = calibration.run_a0_calibration(pp, corpus, output)
    oracle = SESSION / "oracle"
    oracle.mkdir()
    for name in ("power.json", "shortcuts.json", "summary.json", "freeze-manifest.json"):
        write_new(oracle / name, read_independent(output / name))
    write_new(oracle / "returned-summary.json", stable(result))
    metadata = {"root": str(SESSION), "device": SESSION_ID[0], "inode": SESSION_ID[1],
                "files": {p.name: hashlib.sha256(read_independent(p)).hexdigest()
                          for p in oracle.iterdir()}}
    print("BASELINE_ORACLE=" + json.dumps(metadata, sort_keys=True))
    print("SYNTHETIC_SESSION_PRESERVED=" + str(SESSION))

class ProspectiveTests(unittest.TestCase):
    def function(self, name):
        self.assertTrue(hasattr(shortcuts, name), f"missing prospective behavior: {name}")
        return getattr(shortcuts, name)

    def test_legacy_complete_artifact_bytes_match_independent_preedit_oracle(self):
        metadata = json.loads(os.environ["A0X_BASELINE_ORACLE"])
        root = Path(metadata["root"])
        self.assertTrue(str(root).startswith("/private/tmp/a0x-d1d7-synthetic-"))
        self.assertNotIn("..", root.parts)
        current = os.lstat(root)
        self.assertTrue(stat.S_ISDIR(current.st_mode))
        self.assertEqual((current.st_dev, current.st_ino), (metadata["device"], metadata["inode"]))
        cases, targets, protocol = fixture()
        pp, corpus, output = materialize(cases, targets, protocol)
        result = calibration.run_a0_calibration(pp, corpus, output)
        for name, digest in metadata["files"].items():
            self.assertIn(name, {"power.json", "shortcuts.json", "summary.json", "freeze-manifest.json", "returned-summary.json"})
            expected = read_independent(root / "oracle" / name, digest)
            actual = stable(result) if name == "returned-summary.json" else read_independent(output / name)
            self.assertEqual(actual, expected, name)

    def test_sentinel_requires_both_inclusive_unrounded_boundaries(self):
        sentinel = self.function("_v2_sentinel")
        self.assertTrue(sentinel(Fraction(13, 20), Fraction(1, 10)))
        self.assertFalse(sentinel(Fraction(13, 20) - Fraction(1, 10**20), Fraction(1, 10)))
        self.assertFalse(sentinel(Fraction(13, 20), Fraction(1, 10) - Fraction(1, 10**20)))

    def test_fixed_registry_absent_class_contributes_zero(self):
        metric = self.function("_v2_metric")
        self.assertEqual(metric(["a","a","b","b"], ["a","b","b","b"], ["a","b","c"]), Fraction(22,45))
        with self.assertRaises(ValueError): metric(["a"], ["unknown"], ["a","b"])
        with self.assertRaises(LookupError): metric(["a"], [], ["a","b"])
        with self.assertRaises(LookupError): metric([], [], ["a","b"])

    def test_equal_fold_then_domain_weights_and_paired_margin(self):
        aggregate = self.function("_v2_aggregate")
        rows = [{"domain":"d1","f1":Fraction(1),"baseline":Fraction(0)},
                {"domain":"d1","f1":Fraction(0),"baseline":Fraction(0)},
                {"domain":"d2","f1":Fraction(0),"baseline":Fraction(0)}]
        f, m, domains = aggregate(rows)
        self.assertEqual((f,m), (Fraction(1,4),Fraction(1,4)))
        self.assertEqual(domains["d1"], (Fraction(1,2),Fraction(1,2)))

    def test_training_only_majority_utf8_ties(self):
        majority = self.function("_v2_majority")
        self.assertEqual(majority(["b","a"], ["a","b"]), "a")
        self.assertEqual(majority(["b","b","a"], ["a","b"]), "b")

    def test_required_control_precedence_never_exempts_random(self):
        gate = self.function("_v2_gate")
        statuses = {name:"PASS" for name in CONTROLS}
        self.assertEqual(gate(statuses), "PASS")
        del statuses["random_label_controls"]
        self.assertEqual(gate(statuses), "UNEVALUABLE")
        statuses["random_label_controls"] = "NON_INTERPRETABLE"
        self.assertEqual(gate(statuses), "NON_INTERPRETABLE")
        statuses["family_leakage_detection"] = "FAIL"
        self.assertEqual(gate(statuses), "FAIL")
        statuses["family_leakage_detection"] = "DIAGNOSTIC"
        self.assertEqual(gate(statuses), "FAIL")

    def test_normalization_keeps_case_spaces_punctuation_and_utf8(self):
        normalize = self.function("_v2_normalize")
        self.assertEqual(normalize("cafe\u0301\r\nX\rY"), "café\nX\nY".encode())
        self.assertNotEqual(normalize("A "), normalize("a"))
        self.assertNotEqual(normalize("x!"), normalize("x"))
        with self.assertRaises(ValueError): normalize("\ud800")

    def test_selection_rejected_before_any_input_read(self):
        calls = ((shortcuts.audit_a0_shortcuts, ("absent-cases","absent-targets","absent-protocol")),
                 (calibration.run_a0_calibration, ("absent-protocol","absent-corpus","absent-output")))
        for function, args in calls:
            try:
                with self.assertRaises(ValueError):
                    function(*args, method_selection={**SELECTION, "leg":"R1"})
                with self.assertRaises(ValueError):
                    function(*args, mechanical_evidence={})
            except TypeError as exc:
                self.fail(f"missing opt-in pre-I/O rejection: {exc}")

    def test_real_consumer_missing_evidence_is_unevaluable_not_pass(self):
        cases, targets, protocol = fixture()
        try:
            result, output = consumer(cases, targets, protocol, None)
        except TypeError as exc:
            self.fail(f"missing real consumer propagation: {exc}")
        self.assertEqual(result["power_status"], "pass")
        self.assertEqual(result["status"], "UNEVALUABLE")
        self.assertEqual(result["shortcut_status"], "UNEVALUABLE")
        self.assertFalse(result["production_qualified"])

    def test_real_four_file_consumer_complete_fixture_passes_narrow_gate(self):
        cases, targets, protocol = fixture()
        try:
            result, output = consumer(cases, targets, protocol, mechanics(cases))
        except TypeError as exc:
            self.fail(f"missing genuine v2 consumer: {exc}")
        self.assertEqual(result["status"], "PASS")
        payload = json.loads(read_independent(output/"shortcuts.json"))
        self.assertEqual(set(payload["controls"]), set(CONTROLS))
        self.assertTrue(all(item["status"]=="PASS" for item in payload["controls"].values()))
        self.assertFalse(payload["mechanical_freeze_independently_verified"])
        self.assertIn("exact-normalized-only", payload["duplicate_coverage"])

    def test_missing_schedule_is_unevaluable_and_hash_mismatch_is_fail(self):
        cases, targets, protocol = fixture()
        evidence = mechanics(cases)
        del evidence["contract"]["units"]
        self.assertEqual(audit(cases,targets,protocol,rebind(evidence))["status"], "UNEVALUABLE")
        evidence = mechanics(cases); evidence["sha256"]="0"*64
        self.assertEqual(audit(cases,targets,protocol,evidence)["status"], "FAIL")

    def test_unknown_labels_and_invalid_binding_fail(self):
        cases, targets, protocol = fixture()
        targets[0]["operator_proxy_family"]="unknown"
        self.assertEqual(audit(cases,targets,protocol,mechanics(cases))["status"], "FAIL")
        cases, targets, protocol = fixture()
        evidence = mechanics(cases); evidence["contract"]["unexpected"]="exemption"
        self.assertEqual(audit(cases,targets,protocol,rebind(evidence))["status"], "FAIL")

    def test_adverse_view_and_power_failure_propagate(self):
        cases, targets, protocol = fixture()
        for row,target in zip(cases, targets):
            row["initial_state"]=target["operator_proxy_family"]
        result,_=consumer(cases,targets,protocol,mechanics(cases))
        self.assertEqual(result["status"], "NON_INTERPRETABLE")
        protocol["predeclared_calibration_rule"]["permutation_budgets"]=[1]
        result,_=consumer(cases,targets,protocol,mechanics(cases))
        self.assertEqual(result["status"], "FAIL")

    def test_random_controls_permute_training_only_and_keep_family_grouping(self):
        cases, targets, protocol = fixture()
        report=audit(cases,targets,protocol,mechanics(cases))
        random_labels=report["controls"]["random_label_controls"]["evaluations"]
        self.assertEqual(len(random_labels),6)
        for evaluation in random_labels:
            for unit in evaluation["units"]:
                self.assertCountEqual(unit["training_labels"],unit["permuted_training_labels"])
                expected=[target["operator_proxy_family"] for target in targets if target["case_id"] in unit["test_ids"]]
                self.assertEqual(unit["heldout_labels"],expected)
        partitions=report["controls"]["random_partition_controls"]["evaluations"]
        self.assertEqual(len(partitions),6)
        for evaluation in partitions:
            for unit in evaluation["units"]:
                self.assertFalse(set(unit["train_families"]) & set(unit["test_families"]))

    def test_random_view_crosswalk_cannot_drop_any_applicable_view(self):
        cases, targets, protocol = fixture()
        evidence=mechanics(cases); evidence["contract"]["control_views"]["random_label_controls"]=["bow"]
        self.assertEqual(audit(cases,targets,protocol,rebind(evidence))["status"],"FAIL")

    def test_partition_assignment_mismatch_fails_not_resampled(self):
        cases, targets, protocol=fixture()
        evidence=mechanics(cases)
        assignment=evidence["contract"]["partition_assignments"]["replica-0"]["d0"]
        assignment["train_families"],assignment["test_families"]=assignment["test_families"],assignment["train_families"]
        self.assertEqual(audit(cases,targets,protocol,rebind(evidence))["status"],"FAIL")

    def test_exact_duplicate_across_family_boundary_is_fail(self):
        cases,targets,protocol=fixture()
        cases[0]["problem"]="café\r\nX"; cases[4]["problem"]="cafe\u0301\nX"
        report=audit(cases,targets,protocol,mechanics(cases))
        self.assertEqual(report["controls"]["duplicate_and_near_duplicate_detection"]["status"],"FAIL")
        self.assertEqual(report["status"],"FAIL")

    def test_fold_reuse_alone_is_not_leakage(self):
        cases,targets,protocol=fixture()
        report=audit(cases,targets,protocol,mechanics(cases))
        self.assertEqual(report["controls"]["family_leakage_detection"]["status"],"PASS")
        self.assertEqual(report["controls"]["duplicate_and_near_duplicate_detection"]["status"],"PASS")

    def test_family_crossing_same_boundary_fails(self):
        cases,targets,protocol=fixture()
        cases[4]["problem_family_id"]=cases[0]["problem_family_id"]
        report=audit(cases,targets,protocol,mechanics(cases))
        self.assertEqual(report["controls"]["family_leakage_detection"]["status"],"FAIL")
        self.assertEqual(report["status"],"FAIL")

    def test_random_partition_duplicate_crossing_is_checked_per_replica(self):
        cases,targets,protocol=fixture()
        cases[2]["problem"]=cases[0]["problem"]
        evidence=mechanics(cases)
        evidence["contract"]["replicas"].append({"id":"replica-1","seed":1})
        evidence["contract"]["partition_assignments"]["replica-1"]={
            f"d{i}":{"train_families":[f"d{i}f1"],"test_families":[f"d{i}f0"]}
            for i in range(6)}
        report=audit(cases,targets,protocol,rebind(evidence))
        duplicate=report["controls"]["duplicate_and_near_duplicate_detection"]
        self.assertEqual(duplicate["status"],"FAIL")
        units={issue["unit"] for issue in duplicate["issues"]}
        self.assertTrue({"replica-0:d0","replica-1:d0"}<=units)
        self.assertEqual(report["status"],"FAIL")

    def test_malformed_mechanical_containers_are_fail_not_missing(self):
        for field in ("views","units","replicas","partition_train_families",
                      "partition_assignments","payload_stages"):
            with self.subTest(field=field):
                cases,targets,protocol=fixture()
                evidence=mechanics(cases)
                evidence["contract"][field]="not-the-required-container"
                self.assertEqual(audit(cases,targets,protocol,rebind(evidence))["status"],"FAIL")

    def test_malformed_protocol_control_mapping_is_fail_closed(self):
        cases,targets,protocol=fixture()
        protocol["shortcut_evaluation"]=[]
        self.assertEqual(audit(cases,targets,protocol,mechanics(cases))["status"],"FAIL")

    def test_multiple_replicas_remain_separate_for_every_view(self):
        cases,targets,protocol=fixture()
        evidence=mechanics(cases)
        evidence["contract"]["replicas"].append({"id":"replica-1","seed":1})
        evidence["contract"]["partition_assignments"]["replica-1"]={
            f"d{i}":{"train_families":[f"d{i}f1"],"test_families":[f"d{i}f0"]}
            for i in range(6)}
        report=audit(cases,targets,protocol,rebind(evidence))
        for name in ("random_label_controls","random_partition_controls"):
            evaluations=report["controls"][name]["evaluations"]
            self.assertEqual(len(evaluations),12)
            self.assertEqual({(e["view"],e["replica"]) for e in evaluations},
                {(view,replica) for view in evidence["contract"]["views"]
                 for replica in ("replica-0","replica-1")})

    def test_validated_contract_retained_byte_bound_without_caller_alias(self):
        cases,targets,protocol=fixture()
        evidence=mechanics(cases)
        expected=stable(evidence["contract"])
        result,output=consumer(cases,targets,protocol,evidence)
        report=json.loads(read_independent(output/"shortcuts.json"))
        self.assertIn("mechanical_evidence_contract",report)
        self.assertEqual(stable(report["mechanical_evidence_contract"]),expected)
        self.assertEqual(hashlib.sha256(expected).hexdigest(),report["mechanical_evidence_sha256"])
        self.assertEqual(report["mechanical_evidence_validation"],"validated")
        for field in ("algorithm","unicode_version","views","payload_stages","boundaries"):
            self.assertEqual(report["mechanical_evidence_contract"][field],evidence["contract"][field])
        direct=audit(cases,targets,protocol,evidence)
        evidence["contract"]["views"]["bow"]["fields"].append("solution")
        self.assertEqual(stable(direct["mechanical_evidence_contract"]),expected)
        self.assertFalse(report["mechanical_freeze_independently_verified"])
        self.assertFalse(result["production_qualified"])

    def test_unvalidated_contract_never_exported_as_validated_evidence(self):
        for mode in ("absent","bad-digest","missing-field","bad-mode"):
            with self.subTest(mode=mode):
                cases,targets,protocol=fixture()
                evidence=mechanics(cases)
                if mode=="absent": evidence=None
                elif mode=="bad-digest": evidence["sha256"]="0"*64
                elif mode=="missing-field":
                    del evidence["contract"]["units"]; rebind(evidence)
                else:
                    evidence["contract"]["normalization"]="unsupported"; rebind(evidence)
                report=audit(cases,targets,protocol,evidence)
                self.assertIn("mechanical_evidence_contract",report)
                self.assertIsNone(report["mechanical_evidence_contract"])
                self.assertIsNone(report["mechanical_evidence_sha256"])
                self.assertEqual(report["mechanical_evidence_validation"],"UNVERIFIED")
                self.assertEqual(report["evaluated_integrity_scopes"],[])

    def test_integrity_scope_registry_covers_original_and_each_derived_replica(self):
        cases,targets,protocol=fixture()
        evidence=mechanics(cases)
        evidence["contract"]["replicas"].append({"id":"replica-1","seed":1})
        evidence["contract"]["partition_assignments"]["replica-1"]={
            f"d{i}":{"train_families":[f"d{i}f1"],"test_families":[f"d{i}f0"]}
            for i in range(6)}
        report=audit(cases,targets,protocol,rebind(evidence))
        self.assertIn("evaluated_integrity_scopes",report)
        scopes=report["evaluated_integrity_scopes"]
        self.assertEqual(len(scopes),18)
        self.assertEqual({(s["scope_kind"],s["replica"],s["domain"]) for s in scopes},
            {("original_lodo",None,f"d{i}") for i in range(6)} |
            {("derived_random_partition",replica,f"d{i}")
             for replica in ("replica-0","replica-1") for i in range(6)})
        by_id={row["case_id"]:row for row in cases}
        for scope in scopes:
            self.assertEqual(scope["boundaries"],[["train","test"]])
            self.assertEqual(scope["payload_stage_ids"],["raw"])
            for side in ("train","test"):
                self.assertEqual(scope[side+"_families"],
                    sorted({by_id[c]["problem_family_id"] for c in scope[side+"_ids"]}))
            if scope["scope_kind"]=="original_lodo":
                unit=next(u for u in evidence["contract"]["units"] if u["id"]==scope["unit"])
                self.assertEqual(scope["train_ids"],unit["train_ids"])
                self.assertEqual(scope["test_ids"],unit["test_ids"])
            else:
                assignment=evidence["contract"]["partition_assignments"][scope["replica"]][scope["domain"]]
                for side in ("train","test"):
                    self.assertEqual(scope[side+"_families"],assignment[side+"_families"])

    def test_duplicate_issues_retain_case_family_and_scope_identities(self):
        for kind in ("original","derived"):
            with self.subTest(kind=kind):
                cases,targets,protocol=fixture()
                cases[4 if kind=="original" else 2]["problem"]=cases[0]["problem"]
                report=audit(cases,targets,protocol,mechanics(cases))
                issues=report["controls"]["duplicate_and_near_duplicate_detection"]["issues"]
                self.assertTrue(issues)
                by_id={row["case_id"]:row for row in cases}
                scopes={ (s["scope_kind"],s["replica"],s["unit"]):s
                         for s in report.get("evaluated_integrity_scopes",[]) }
                for issue in issues:
                    self.assertIn("train_family",issue)
                    self.assertEqual(issue["train_family"],by_id[issue["train_case"]]["problem_family_id"])
                    self.assertEqual(issue["test_family"],by_id[issue["test_case"]]["problem_family_id"])
                    key=(issue["scope_kind"],issue["replica"],issue["unit"])
                    self.assertIn(key,scopes)
                    self.assertIn(issue["train_case"],scopes[key]["train_ids"])
                    self.assertIn(issue["test_case"],scopes[key]["test_ids"])

    def test_missing_control_key_and_target_identity_are_not_malformed_values(self):
        cases,targets,protocol=fixture()
        del protocol["shortcut_evaluation"]["a0_controls"]
        self.assertEqual(audit(cases,targets,protocol,mechanics(cases))["status"],"UNEVALUABLE")
        for invalid in (None,{},"all",[],CONTROLS[:-1]):
            with self.subTest(controls=invalid):
                cases,targets,protocol=fixture()
                protocol["shortcut_evaluation"]["a0_controls"]=invalid
                self.assertEqual(audit(cases,targets,protocol,mechanics(cases))["status"],"FAIL")
        cases,targets,protocol=fixture()
        del targets[0]["case_id"]
        self.assertEqual(audit(cases,targets,protocol,mechanics(cases))["status"],"UNEVALUABLE")
        for invalid in (None,"",[]," spaced "):
            with self.subTest(identity=invalid):
                cases,targets,protocol=fixture()
                targets[0]["case_id"]=invalid
                self.assertEqual(audit(cases,targets,protocol,mechanics(cases))["status"],"FAIL")

    def test_lodo_adverse_domain_cannot_be_averaged_away(self):
        rows={
            "ta":{"case_id":"ta","problem_family_id":"ta","label":"a","initial_state":"alpha"},
            "tb":{"case_id":"tb","problem_family_id":"tb","label":"b","initial_state":"beta"},
            "x0":{"case_id":"x0","problem_family_id":"x0","label":"a","initial_state":"alpha"},
            "x1":{"case_id":"x1","problem_family_id":"x1","label":"b","initial_state":"beta"},
            "y0":{"case_id":"y0","problem_family_id":"y0","label":"b","initial_state":"alpha"},
            "y1":{"case_id":"y1","problem_family_id":"y1","label":"a","initial_state":"beta"},
        }
        units=[{"id":"u0","fold":"f0","domain":"d0","train_ids":["ta","tb"],"test_ids":["x0","x1"]},
               {"id":"u1","fold":"f0","domain":"d1","train_ids":["ta","tb"],"test_ids":["y0","y1"]}]
        contract={"classes":["a","b"],"views":{"simple":{"kind":"word_unigrams","fields":["initial_state"]}}}
        result=self.function("_v2_evaluate")(rows,units,contract,"simple",lodo=True)
        self.assertEqual(result["f1"]["numerator"],1)
        self.assertEqual(result["f1"]["denominator"],2)
        self.assertEqual(result["status"],"NON_INTERPRETABLE")

if __name__ == "__main__":
    if MODE == "baseline":
        baseline()
    else:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(ProspectiveTests)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        print("SYNTHETIC_SESSION_PRESERVED="+str(SESSION))
        raise SystemExit(0 if result.wasSuccessful() else 1)
