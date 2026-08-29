PYTHONPATH := src

.PHONY: test validate docs-audit check schema-cross-validate a0x-synthetic-verify a0x-no-model-verify a0x-material-a0-smollm2-360m a0x-material-a0-qwen3-0-6b-base a0x-material-a0-gpt2 a0x-material-a0-smollm2-135m a0x-material-a0-gpt-neo-125m a0x-material-a0-qwen2-5-0-5b a0x-material-r1-smollm2-360m a0x-material-r1-qwen3-0-6b-base a0x-material-r1-gpt2 a0x-material-r1-smollm2-135m a0x-material-r1-gpt-neo-125m a0x-material-r1-qwen2-5-0-5b exp002-contract-verify exp002-question-bank-audit exp002-publication-verify exp002-runner-test exp002-stage-preflight exp002-review-packet-verify exp002-auto-verify exp002-auto-stage-preflight no-model-quickstart preflight-status preflight-plan preflight-doctor preflight-dry-run preflight-run preflight-verify preflight-postflight model-preflight dataset-audit dataset-wave1-audit wave1-surface-audit wave1-surface-audit-render wave1-annotation-audit h1-annotation-audit readiness lab00 lab00-render lab01-setup lab01-acquire lab01-bootstrap lab01 lab01-render lab01-representations lab02 lab02-render lab03 lab03-render lab04 lab04-render lab05 lab05-render annotate annotate-serve annotate-wave1 pilot-export-evaluator stage1-pilot-validate stage1-pilot-smoke lab lab-render a0-corpus a0-calibrate a0r1-verify a0r1-execution-verify a0r1-freeze a0r1-run a0r1-run-verify a0r1-publication-verify a0r2-acquisition-verify a0r2-approval-dossier-verify a0r2-feasibility-contract-verify a0r2-feasibility-run a0r2-feasibility-verify a0r2-execution-verify a0r2-run a0r2-run-verify a0r2-publication-verify a0r2c1-contract-verify a0r2c1-run a0r2c2-contract-verify a0r2c2-run a0r2c3-contract-verify a0r2c3-run a0

LAB01_MODEL_ROOT ?= artifacts/models/pythia-70m-deduped-e93a9faa
LAB01_PYTHON ?= .venv/bin/python
LAB01_ADMISSION_TIMEOUT ?= 30
A0R1_RUN_ID ?= a0r1-v1.0.0-e93a9faa-r1
A0R1_CREATED_AT ?=
A0R2_MODEL_ROOT ?= artifacts/models/smollm2-360m-f8027fd0
A0R2_PYTHON ?= .venv/bin/python
A0R2_CREATED_AT ?=
A0R2_ADMISSION_TIMEOUT ?= 30
A0R2_RUN_ID ?= a0r2-v1.0.0-f8027fd0-r1
A0R2_AUTHORIZATION_RECEIPT ?= results/a0r2/preexecution/smollm2-360m-f8027fd0/sealed-execution-authorization.json
A0R2C1_RUN_ID ?= a0r2c1-v1.0.0-f8027fd0-r1
A0R2C1_AUTHORIZATION_RECEIPT ?= results/a0r2c1/preexecution/sealed-execution-authorization.json
A0R2C2_RUN_ID ?= a0r2c2-v1.0.0-f8027fd0-r1
A0R2C2_AUTHORIZATION_RECEIPT ?= results/a0r2c2/preexecution/sealed-execution-authorization.json
A0R2C3_RUN_ID ?= a0r2c3-analysis-only-v1.0.0-f8027fd0-r1
A0R2C3_AUTHORIZATION_RECEIPT ?= results/a0r2c3/preexecution/analysis-authorization.json

LAB_SUITE_OUTPUT ?= artifacts/lab/index.html
ANNOTATION_RATER_ID ?= local_rater
ANNOTATION_OUTPUT ?= artifacts/annotations/dataset-annotations.jsonl
ANNOTATION_PORT ?= 8765

test:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests -p "test_*.py"

validate:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/case.schema.json tests/fixtures/case_valid.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/study.schema.json experiments/000-template/manifest.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/study.schema.json experiments/001-stage1-pilot/manifest.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/run.schema.json experiments/000-template/run.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/dataset-registry.schema.json data/registry.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/claim.schema.json data/claims.jsonl
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/lab01-manifest.schema.json experiments/lab01-model-anatomy/manifest.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/dataset-annotation.schema.json data/pilot/dataset-annotations.jsonl
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/annotation-guide.schema.json experiments/001-stage1-pilot/annotation-guide.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/candidate-batch.schema.json data/candidates/wave1-manifest.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/triz-reference-registry.schema.json data/triz-reference-sources.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/triz-principle-reference.schema.json data/triz-reference/principles.jsonl
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/triz-web-corpus.schema.json data/triz-consulting-web-corpus.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/a0r2-sealed-execution-approval-dossier.schema.json experiments/a0r2-independent-model/sealed-execution-approval-dossier.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/a0r2-sealed-execution-authorization.schema.json results/a0r2/preexecution/smollm2-360m-f8027fd0/sealed-execution-authorization.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/a0r2c1-correction-contract.schema.json experiments/a0r2c1-tokenizer-correction/contract.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/a0r2c1-tokenizer-compatibility.schema.json results/a0r2c1/preexecution/tokenizer-compatibility.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/a0r2c1-sealed-execution-authorization.schema.json results/a0r2c1/preexecution/sealed-execution-authorization.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/a0r2c2-correction-contract.schema.json experiments/a0r2c2-shape-correction/contract.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/a0r2c3-analysis-contract.schema.json experiments/a0r2c3-analysis-only-recovery/contract.json
	python3 -c 'import json; json.load(open("schemas/a0r2c2-sealed-execution-authorization.schema.json"))'
	python3 -c 'import json; json.load(open("schemas/blinded-annotation-audit.schema.json"))'
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/case.schema.json data/candidates/wave1-model-generated.jsonl
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/lab03-config.schema.json experiments/lab03-behavioral-baselines/config.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/lab03-config.schema.json experiments/wave1-surface-audit/config.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/lab03-result.schema.json results/lab03/behavioral-baselines/summary.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/representation-extractor-config.schema.json experiments/lab01-model-representations/config.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/lab03-result.schema.json results/wave1/surface-audit/summary.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/lab05-config.schema.json experiments/lab05-candidate-directions/config.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/lab05-result.schema.json results/lab05/candidate-directions/summary.json
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli claims-audit --registry data/claims.jsonl --root .
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/case.schema.json tests/fixtures/case_valid.jsonl
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/case.schema.json data/pilot/cases.jsonl
	for path in schemas/case.schema.json schemas/study.schema.json schemas/run.schema.json schemas/dataset-registry.schema.json schemas/claim.schema.json schemas/triz-reference-registry.schema.json schemas/triz-principle-reference.schema.json schemas/triz-web-corpus.schema.json schemas/a0r2-sealed-execution-approval-dossier.schema.json schemas/a0r2-sealed-execution-authorization.schema.json data/registry.json data/triz-reference-sources.json data/triz-consulting-web-corpus.json experiments/a0r2-independent-model/sealed-execution-approval-dossier.json results/a0r2/preexecution/smollm2-360m-f8027fd0/sealed-execution-authorization.json experiments/000-template/manifest.json experiments/000-template/run.json; do python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$$path" || (echo "latent-triz: $$path:0:0: invalid JSON"; exit 1); done

docs-audit:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli docs-audit --profile docs/okf-profile.toml --root . --as-of-date "$$(python3 -c 'from datetime import date; print(date.today().isoformat())')"

check:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/repository_check.py

schema-cross-validate:
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) scripts/schema_cross_validate.py

a0x-synthetic-verify:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_contract_check.py --phase synthetic
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest tests.test_a0x_runner tests.test_a0x_contract_check tests.test_a0x_material tests.test_a0x_material_child tests.test_a0x_material_contract tests.test_a0x_material_runtime tests.test_a0x_runtime_bundle tests.test_a0x_runtime_readiness tests.test_a0x_production_adapter tests.test_a0x_ccp_executor tests.test_a0x_contract tests.test_a0x_preflight tests.test_a0x_freeze tests.test_a0x_frozen_package tests.test_a0x_schemas tests.test_a0x_activations tests.test_a0x_a0_analysis tests.test_a0x_r1_analysis tests.test_a0x_report tests.test_a0x_verify tests.test_a0x_execution tests.test_a0x_model_adapter tests.test_a0x_matrix_plan_binding
	@echo "A0X synthetic implementation verified: no model, tokenizer, sealed target, or CCP access."

a0x-no-model-verify:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_contract_check.py --phase frozen
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest tests.test_a0x_frozen_package -v
	@echo "A0X frozen package verified: zero model loads, tokenizer constructions, sealed-target reads, CCP invocations, and remote mutations."

a0x-material-a0-smollm2-360m:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/a0/smollm2_360m.json

a0x-material-a0-qwen3-0-6b-base:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/a0/qwen3_0_6b_base.json

a0x-material-a0-gpt2:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/a0/gpt2.json

a0x-material-a0-smollm2-135m:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/a0/smollm2_135m.json

a0x-material-a0-gpt-neo-125m:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/a0/gpt_neo_125m.json

a0x-material-a0-qwen2-5-0-5b:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/a0/qwen2_5_0_5b.json

a0x-material-r1-smollm2-360m:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/r1/smollm2_360m.json

a0x-material-r1-qwen3-0-6b-base:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/r1/qwen3_0_6b_base.json

a0x-material-r1-gpt2:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/r1/gpt2.json

a0x-material-r1-smollm2-135m:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/r1/smollm2_135m.json

a0x-material-r1-gpt-neo-125m:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/r1/gpt_neo_125m.json

a0x-material-r1-qwen2-5-0-5b:
	PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/r1/qwen2_5_0_5b.json

exp002-contract-verify:
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) scripts/exp002_contract_check.py

exp002-question-bank-audit: exp002-contract-verify
	@echo "EXP-002 question bank and label-surface audit passed without model or sealed-target access."

exp002-publication-verify:
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) scripts/exp002_publication_verify.py

exp002-runner-test:
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) -m unittest tests.test_exp002_runner tests.test_exp002_stage_cli tests.test_exp002_answer_key tests.test_exp002_freeze_answer_key_cli tests.test_exp002_transfer_corpus tests.test_exp002_validate_transfer_corpus_cli tests.test_exp002_validate_review_packet tests.test_exp002_stage_preflight tests.test_exp002_stage_gate tests.test_exp002_expert_review tests.test_exp002_source_familiarity tests.test_exp002_power tests.test_exp002_schema_guards tests.test_exp002_execution

exp002-stage-preflight:
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) scripts/exp002_stage_preflight.py --stage EXP-002B
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) scripts/exp002_stage_preflight.py --stage EXP-002C

exp002-review-packet-verify:
	@test -n "$(PACKET)" || (echo "PACKET=/path/to/reviewer-packet.json is required"; exit 2)
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) scripts/exp002_validate_review_packet.py --packet "$(PACKET)"

exp002-auto-verify:
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) scripts/exp002_auto_contract_check.py
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) -m unittest tests.test_exp002_auto_contract tests.test_exp002_auto_fixtures tests.test_exp002_auto_schedule tests.test_exp002_auto_execution tests.test_exp002_auto_analysis tests.test_exp002_auto_stage_gate tests.test_exp002_auto_report tests.test_exp002_auto_contract_check tests.test_exp002_auto_cli tests.test_exp002_auto_material
	@echo "EXP-002-AUTO no-model checkpoint passed: no model, tokenizer, network, or sealed target access."

exp002-auto-stage-preflight:
	@echo "EXP-002-AUTO remains approval-required; use the exact hash-bound dossier only after a new operator authorization."

no-model-quickstart:
	@echo "Latent-TRIZ no-model quickstart: synthetic dashboard, schemas, H1 packet, CV2, and Lab06 readiness"
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) -m latent_triz.cli lab-suite --root . --output $(LAB_SUITE_OUTPUT)
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) scripts/schema_cross_validate.py
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) scripts/h1_packet_audit.py
	PYTHONPATH=$(PYTHONPATH) $(LAB01_PYTHON) -m unittest tests.test_cv2_lab06_schemas tests.test_h1_packet_audit
	@echo "No model, sealed target, training, generation, or dense scientific output was accessed."

a0-corpus:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli a0-corpus \
	  --protocol experiments/a0-automated-weak-proxy/protocol.json \
	  --output-dir data/a0
	@echo "A0 foundation generated. Activation and statistical stages are not yet executed."

a0-calibrate:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli a0-calibrate \
	  --protocol experiments/a0-automated-weak-proxy/protocol.json \
	  --corpus-dir data/a0 \
	  --output-dir results/a0/calibration
	@echo "A0 calibration passed. Sealed targets were not accessed."

a0r1-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli a0r1-verify --root .
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli a0r1-execution-verify --root .
	@echo "A0-R1 pre-output corpus and audits reproduced byte-for-byte; no model output was accessed."

a0r1-execution-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli a0r1-execution-verify --root .

a0r1-freeze:
	@echo "A0-R1 is frozen; verifying the immutable tracked package."
	$(MAKE) a0r1-verify

a0r1-run:
	@test -x "$(LAB01_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	@test -n "$(A0R1_CREATED_AT)" || (echo "A0R1_CREATED_AT must be set"; exit 2)
	PYTHONPATH=$(PYTHONPATH) commit-ci-preflight guard exec \
	  --admission-timeout-seconds "$(LAB01_ADMISSION_TIMEOUT)" \
	  --timeout-seconds 1800 -- \
	  "$(LAB01_PYTHON)" -m latent_triz.a0r1_runner \
	  --root . \
	  --model-root "$(LAB01_MODEL_ROOT)" \
	  --run-id "$(A0R1_RUN_ID)" \
	  --created-at "$(A0R1_CREATED_AT)" \
	  --stage all
	@echo "A0-R1 sealed result: results/a0r1/$(A0R1_RUN_ID)/statistical-result.json"

a0r1-run-verify:
	@test -x "$(LAB01_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	PYTHONPATH=$(PYTHONPATH) "$(LAB01_PYTHON)" -m latent_triz.a0r1_runner \
	  --root . \
	  --model-root "$(LAB01_MODEL_ROOT)" \
	  --run-id "$(A0R1_RUN_ID)" \
	  --created-at "$(or $(A0R1_CREATED_AT),2000-01-01T00:00:00Z)" \
	  --stage verify
	@echo "A0-R1 sealed verify result: results/a0r1/$(A0R1_RUN_ID)/statistical-result.json"

a0r1-publication-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.a0r1_report \
	  --stage verify \
	  --package-dir results/a0r1/$(A0R1_RUN_ID) \
	  --external-activation-dir artifacts/a0r1/$(A0R1_RUN_ID)
	@echo "A0-R1 immutable publication package verified; no model or sealed target was accessed."

a0r2-acquisition-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.a0r2_acquire --verify
	@echo "A0-R2 exact snapshot integrity verified; the model was not loaded."

a0r2-feasibility-contract-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest tests.test_a0r2_feasibility tests.test_a0r2_feasibility_schema
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate \
	  --schema schemas/a0r2-feasibility-contract.schema.json \
	  experiments/a0r2-independent-model/feasibility-contract.json
	@echo "A0-R2 feasibility contract verified; the model was not loaded."

a0r2-approval-dossier-verify:
	@test -x "$(A0R2_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	PYTHONPATH=$(PYTHONPATH) "$(A0R2_PYTHON)" -m unittest tests.test_a0r2_approval_dossier
	PYTHONPATH=$(PYTHONPATH) "$(A0R2_PYTHON)" -m latent_triz.cli validate \
	  --schema schemas/a0r2-sealed-execution-approval-dossier.schema.json \
	  experiments/a0r2-independent-model/sealed-execution-approval-dossier.json
	@echo "A0-R2.3 historical approval dossier verified; no target was opened."

a0r2-authorization-verify:
	@test -x "$(A0R2_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	PYTHONPATH=$(PYTHONPATH) "$(A0R2_PYTHON)" -m unittest tests.test_a0r2_authorization
	PYTHONPATH=$(PYTHONPATH) "$(A0R2_PYTHON)" -c 'from latent_triz.a0r2_authorization import verify_a0r2_sealed_execution_authorization; verify_a0r2_sealed_execution_authorization(".")'
	@echo "A0-R2.3 corrective authorization verified; no model or target was accessed."

a0r2-feasibility-run:
	@test -x "$(A0R2_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	@test -n "$(A0R2_CREATED_AT)" || (echo "A0R2_CREATED_AT must be set"; exit 2)
	PYTHONPATH=$(PYTHONPATH) commit-ci-preflight guard exec \
	  --admission-timeout-seconds "$(A0R2_ADMISSION_TIMEOUT)" \
	  --timeout-seconds 900 -- \
	  "$(A0R2_PYTHON)" -m latent_triz.a0r2_feasibility \
	  --root . \
	  --model-root "$(A0R2_MODEL_ROOT)" \
	  --created-at "$(A0R2_CREATED_AT)"

a0r2-feasibility-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.a0r2_feasibility --root . --verify-only
	@echo "A0-R2 bounded feasibility receipt verified; no model was loaded."

a0r2-execution-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -c 'from latent_triz.a0r2_execution import verify_a0r2_execution_contract; verify_a0r2_execution_contract(".")'
	@echo "A0-R2 frozen implementation contract verified; no model or sealed target was accessed."

a0r2-run:
	@test -x "$(A0R2_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	@test -n "$(A0R2_CREATED_AT)" || (echo "A0R2_CREATED_AT must be set"; exit 2)
	PYTHONPATH=$(PYTHONPATH) commit-ci-preflight guard exec \
	  --admission-timeout-seconds "$(A0R2_ADMISSION_TIMEOUT)" \
	  --timeout-seconds 1800 -- \
	  "$(A0R2_PYTHON)" -m latent_triz.a0r2_runner \
	  --root . --run-id "$(A0R2_RUN_ID)" --created-at "$(A0R2_CREATED_AT)" \
	  --model-root "$(A0R2_MODEL_ROOT)" --authorization-receipt "$(A0R2_AUTHORIZATION_RECEIPT)" --stage all

a0r2-run-verify:
	@test -x "$(A0R2_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	PYTHONPATH=$(PYTHONPATH) "$(A0R2_PYTHON)" -m latent_triz.a0r2_runner \
	  --root . --run-id "$(A0R2_RUN_ID)" \
	  --created-at "$(or $(A0R2_CREATED_AT),2000-01-01T00:00:00Z)" --stage verify

a0r2-publication-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.a0r2_report \
	  --package-dir "results/a0r2/$(A0R2_RUN_ID)" \
	  --external-dense-dir "artifacts/a0r2/$(A0R2_RUN_ID)" --verify-only
	@echo "A0-R2 immutable package verified; no model or sealed target was accessed."

a0r2c1-contract-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -c 'from latent_triz.a0r2c1_authorization import verify_a0r2c1_contract; verify_a0r2c1_contract(".")'
	@echo "A0-R2-C1 correction contract verified; no model or sealed target was accessed."

a0r2c1-run:
	@test -x "$(A0R2_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	@test -n "$(A0R2_CREATED_AT)" || (echo "A0R2_CREATED_AT must be set"; exit 2)
	PYTHONPATH=$(PYTHONPATH) commit-ci-preflight guard exec \
	  --admission-timeout-seconds "$(A0R2_ADMISSION_TIMEOUT)" \
	  --timeout-seconds 1800 -- \
	  "$(A0R2_PYTHON)" -m latent_triz.a0r2c1_runner \
	  --root . --run-id "$(A0R2C1_RUN_ID)" --created-at "$(A0R2_CREATED_AT)" \
	  --model-root "$(A0R2_MODEL_ROOT)" --authorization-receipt "$(A0R2C1_AUTHORIZATION_RECEIPT)" --stage all

a0r2c2-contract-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -c 'from latent_triz.a0r2c2_authorization import verify_a0r2c2_contract; verify_a0r2c2_contract(".")'
	@echo "A0-R2-C2 correction contract verified; no model or sealed target was accessed."

a0r2c3-contract-verify:
	PYTHONPATH=$(PYTHONPATH) python3 -c 'from latent_triz.a0r2c3_authorization import verify_a0r2c3_contract; verify_a0r2c3_contract(".")'
	@echo "A0-R2-C3 analysis-only contract verified; no model or sealed target was accessed."

a0r2c3-run:
	@test -x "$(A0R2_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	@test -n "$(A0R2_CREATED_AT)" || (echo "A0R2_CREATED_AT must be set"; exit 2)
	PYTHONPATH=$(PYTHONPATH) commit-ci-preflight guard exec \
	  --admission-timeout-seconds "$(A0R2_ADMISSION_TIMEOUT)" \
	  --timeout-seconds 1800 -- \
	  "$(A0R2_PYTHON)" -m latent_triz.a0r2c3_runner \
	  --root . --run-id "$(A0R2C3_RUN_ID)" --created-at "$(A0R2_CREATED_AT)" \
	  --authorization-receipt "$(A0R2C3_AUTHORIZATION_RECEIPT)" --stage all

a0r2c2-run:
	@test -x "$(A0R2_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	@test -n "$(A0R2_CREATED_AT)" || (echo "A0R2_CREATED_AT must be set"; exit 2)
	PYTHONPATH=$(PYTHONPATH) commit-ci-preflight guard exec \
	  --admission-timeout-seconds "$(A0R2_ADMISSION_TIMEOUT)" \
	  --timeout-seconds 1800 -- \
	  "$(A0R2_PYTHON)" -m latent_triz.a0r2c2_runner \
	  --root . --run-id "$(A0R2C2_RUN_ID)" --created-at "$(A0R2_CREATED_AT)" \
	  --model-root "$(A0R2_MODEL_ROOT)" --authorization-receipt "$(A0R2C2_AUTHORIZATION_RECEIPT)" --stage all

a0:
	@test -x "$(LAB01_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	PYTHONPATH=$(PYTHONPATH) commit-ci-preflight guard exec \
	  --admission-timeout-seconds "$(LAB01_ADMISSION_TIMEOUT)" \
	  --timeout-seconds 900 -- \
	  "$(LAB01_PYTHON)" -m latent_triz.a0_runner \
	  --root . \
	  --model-root "$(LAB01_MODEL_ROOT)" \
	  --stage "$$(if test -f results/a0/a0-v1.0.3-e93a9faa/statistical-result.json; then echo verify; else echo all; fi)"
	@echo "A0 sealed result: results/a0/a0-v1.0.3-e93a9faa/statistical-result.json"

preflight-status:
	commit-ci-preflight --version
	git status --short --branch
	git rev-parse HEAD
	commit-ci-preflight resource status --json
	commit-ci-preflight admission status --json
	docker context show
	docker ps -q

preflight-plan:
	commit-ci-preflight plan --config .commit-ci-preflight.toml --matrix-plan-profile matrix-v2-legacy-v1 --json

preflight-doctor:
	commit-ci-preflight doctor --config .commit-ci-preflight.toml --matrix-plan-profile matrix-v2-legacy-v1 --json

preflight-dry-run:
	commit-ci-preflight dry-run --config .commit-ci-preflight.toml --repository . --matrix-plan-profile matrix-v2-legacy-v1 --json

preflight-run:
	commit-ci-preflight run --config .commit-ci-preflight.toml --repository . --generation 1 --matrix-plan-profile matrix-v2-legacy-v1 --json

preflight-verify:
	commit-ci-preflight verify --receipt .ccp/receipt.json --policy .commit-ci-policy-v2.toml --expected-commit "$$(git rev-parse HEAD)"

preflight-postflight:
	commit-ci-preflight admission status --json
	docker ps -q
	commit-ci-preflight resource status --json

model-preflight:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli model-preflight --manifest experiments/001-stage1-pilot/model-candidates.jsonl

dataset-audit:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli dataset-audit --plan experiments/001-stage1-pilot/dataset-plan.json --cases data/pilot/cases.jsonl --mode development

dataset-wave1-audit:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli candidate-audit \
	  --manifest data/candidates/wave1-manifest.json \
	  --cases data/candidates/wave1-model-generated.jsonl

wave1-surface-audit-render:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.lab03_runner \
	  --cases data/candidates/wave1-model-generated.jsonl \
	  --snapshot results/lab02/dataset-anatomy/snapshot_manifest.json \
	  --config experiments/wave1-surface-audit/config.json \
	  --output-dir results/wave1/surface-audit

wave1-surface-audit: wave1-surface-audit-render
	@echo "Wave 1 surface audit: results/wave1/surface-audit/report.html"

wave1-annotation-audit:
	@test -n "$(ANNOTATION_FILES)" || (echo "ANNOTATION_FILES requires one JSONL path per independent rater"; exit 2)
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli annotation-audit \
	  --cases data/candidates/wave1-model-generated.jsonl \
	  --guide experiments/001-stage1-pilot/annotation-guide.json \
	  --schema schemas/dataset-annotation.schema.json \
	  --annotations $(ANNOTATION_FILES) \
	  --minimum-distinct-raters 2 --agreement-threshold 0.8 \
	  --maximum-abstention-rate 0.2 \
	  --output artifacts/annotations/wave1-audit.json

h1-annotation-audit:
	@test -n "$(ANNOTATION_FILES)" || (echo "ANNOTATION_FILES requires exactly three v1.2 H1 JSONL paths"; exit 2)
	@test $$(printf '%s\n' $(ANNOTATION_FILES) | wc -l | tr -d ' ') -eq 3 || (echo "H1 requires exactly three independent files"; exit 2)
	PYTHONPATH=$(PYTHONPATH) python3 scripts/h1_collection_audit.py \
	  --annotations $(ANNOTATION_FILES) \
	  --output artifacts/annotations/h1-v1.2-audit.json

readiness:
	@if [ "$(TARGET)" = "foundation" ]; then \
	  $(MAKE) check; \
	elif [ "$(TARGET)" = "lab01" ]; then \
	  $(MAKE) lab01-render LAB01_MODEL_ROOT="$(LAB01_MODEL_ROOT)"; \
	elif [ "$(TARGET)" = "lab02" ]; then \
	  $(MAKE) lab02-render; \
	elif [ "$(TARGET)" = "lab03" ]; then \
	  $(MAKE) lab03-render; \
	elif [ "$(TARGET)" = "lab04" ]; then \
	  $(MAKE) lab04-render; \
	elif [ "$(TARGET)" = "lab05" ]; then \
	  $(MAKE) lab05-render; \
	elif [ "$(TARGET)" = "exp001" ]; then \
	  $(MAKE) model-preflight; \
	  $(MAKE) dataset-audit; \
	else \
	  echo "TARGET must be foundation, lab01, lab02, lab03, lab04, lab05, or exp001"; exit 2; \
	fi

lab01-setup:
	@test -x "$(LAB01_PYTHON)" || python3.11 -m venv .venv
	@"$(LAB01_PYTHON)" -c "import torch, transformers, safetensors, huggingface_hub" 2>/dev/null || "$(LAB01_PYTHON)" -m pip install -r requirements-lab01.lock

lab01-acquire: lab01-setup
	PYTHONPATH=$(PYTHONPATH) "$(LAB01_PYTHON)" -m latent_triz.lab01_acquire \
	  --model-root "$(LAB01_MODEL_ROOT)" \
	  --allow-download

lab01-render:
	@test -x "$(LAB01_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	PYTHONPATH=$(PYTHONPATH) commit-ci-preflight guard exec \
	  --admission-timeout-seconds "$(LAB01_ADMISSION_TIMEOUT)" \
	  --timeout-seconds 900 -- \
	  "$(LAB01_PYTHON)" -m latent_triz.lab01_runner \
	  --model-root "$(LAB01_MODEL_ROOT)" \
	  --prompts experiments/lab01-model-anatomy/prompts.jsonl \
	  --output-dir results/lab01/model-anatomy

lab01: lab01-render
	@echo "Lab 01 report: results/lab01/model-anatomy/report.html"

lab01-representations:
	@test -x "$(LAB01_PYTHON)" || (echo "Run make lab01-setup first"; exit 2)
	PYTHONPATH=$(PYTHONPATH) commit-ci-preflight guard exec \
	  --admission-timeout-seconds "$(LAB01_ADMISSION_TIMEOUT)" \
	  --timeout-seconds 900 -- \
	  "$(LAB01_PYTHON)" -m latent_triz.representation_extractor \
	  --config experiments/lab01-model-representations/config.json
	@echo "Lab 01 representation extraction: results/lab01/model-representations"

lab01-bootstrap: lab01-acquire
	@$(MAKE) lab01 LAB01_MODEL_ROOT="$(LAB01_MODEL_ROOT)" LAB01_PYTHON="$(LAB01_PYTHON)"

lab02-render:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.lab02_runner \
	  --plan experiments/001-stage1-pilot/dataset-plan.json \
	  --cases data/pilot/cases.jsonl \
	  --annotations data/pilot/dataset-annotations.jsonl \
	  --registry-entry experiments/001-stage1-pilot/dataset-registry-entry.json \
	  --registry-manifest data/registry.json \
	  --output-dir results/lab02/dataset-anatomy

lab02: lab02-render
	@echo "Lab 02 report: results/lab02/dataset-anatomy/report.html"

lab03-render:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.lab03_runner \
	  --cases data/pilot/cases.jsonl \
	  --snapshot results/lab02/dataset-anatomy/snapshot_manifest.json \
	  --config experiments/lab03-behavioral-baselines/config.json \
	  --output-dir results/lab03/behavioral-baselines

lab03: lab03-render
	@echo "Lab 03 report: results/lab03/behavioral-baselines/report.html"

lab04-render:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.lab04_runner \
	  --cases data/pilot/cases.jsonl \
	  --representations data/pilot/representations.jsonl \
	  --config experiments/lab04-decodability/config.json \
	  --predecessor-lab01-summary results/lab01/model-anatomy/parity_report.json \
	  --predecessor-lab02-summary results/lab02/dataset-anatomy/summary.json \
	  --predecessor-lab03-summary results/lab03/behavioral-baselines/summary.json \
	  --output-dir results/lab04/decodability

lab04: lab04-render
	@echo "Lab 04 report: results/lab04/decodability/report.html"

lab05-render:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.lab05_runner \
	  --cases data/pilot/cases.jsonl \
	  --representations data/pilot/representations.jsonl \
	  --config experiments/lab05-candidate-directions/config.json \
	  --predecessor-lab04-summary results/lab04/decodability/summary.json \
	  --output-dir results/lab05/candidate-directions

lab05: lab05-render
	@echo "Lab 05 report: results/lab05/candidate-directions/report.html"

annotate:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli annotation-workbench \
	  --cases data/pilot/cases.jsonl \
	  --guide experiments/001-stage1-pilot/annotation-guide.json \
	  --schema schemas/dataset-annotation.schema.json \
	  --output "$(ANNOTATION_OUTPUT)" --rater-id "$(ANNOTATION_RATER_ID)" \
	  --port "$(ANNOTATION_PORT)" --open

annotate-serve:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli annotation-workbench \
	  --cases data/pilot/cases.jsonl \
	  --guide experiments/001-stage1-pilot/annotation-guide.json \
	  --schema schemas/dataset-annotation.schema.json \
	  --output "$(ANNOTATION_OUTPUT)" --rater-id "$(ANNOTATION_RATER_ID)" \
	  --port "$(ANNOTATION_PORT)"

annotate-wave1:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli annotation-workbench \
	  --cases data/candidates/wave1-model-generated.jsonl \
	  --guide experiments/001-stage1-pilot/annotation-guide.json \
	  --schema schemas/dataset-annotation.schema.json \
	  --output "artifacts/annotations/wave1-$(ANNOTATION_RATER_ID).jsonl" \
	  --rater-id "$(ANNOTATION_RATER_ID)" --port "$(ANNOTATION_PORT)" --open

pilot-export-evaluator:
	@test -n "$(EVALUATOR_OUTPUT)" || (echo "EVALUATOR_OUTPUT is required"; exit 2)
	@test -n "$(ALLOCATION_KEY_OUTPUT)" || (echo "ALLOCATION_KEY_OUTPUT is required"; exit 2)
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli pilot-export-evaluator \
	  --packets data/pilot/packets.jsonl \
	  --responses data/pilot/responses.jsonl \
	  --evaluator-output "$(EVALUATOR_OUTPUT)" \
	  --key-output "$(ALLOCATION_KEY_OUTPUT)"

stage1-pilot-validate:
	for path in schemas/pilot-packet.schema.json schemas/pilot-response.schema.json schemas/pilot-annotation.schema.json schemas/pilot-summary.schema.json schemas/evaluator-packet.schema.json schemas/allocation-key.schema.json; do \
	  python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$$path" || (echo "latent-triz: $$path:0:0: invalid JSON"; exit 1); \
	done
	@if [ -n "$$PILOT_PACKET" ]; then \
	  PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/pilot-packet.schema.json "$$PILOT_PACKET"; \
	fi
	@if [ -n "$$PILOT_RESPONSE" ]; then \
	  PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/pilot-response.schema.json "$$PILOT_RESPONSE"; \
	fi
	@if [ -n "$$PILOT_ANNOTATION" ]; then \
	  PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/pilot-annotation.schema.json "$$PILOT_ANNOTATION"; \
	fi
	@if [ -n "$$PILOT_SUMMARY" ]; then \
	  PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/pilot-summary.schema.json "$$PILOT_SUMMARY"; \
	fi

stage1-pilot-smoke:
	@set -eu; \
	tmpdir="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	cases=data/pilot/cases.jsonl; \
	expected_packets=data/pilot/packets.jsonl; \
	expected_summary=data/pilot/summary.json; \
	responses=data/pilot/responses.jsonl; \
	annotations=data/pilot/annotations.jsonl; \
	tmp_packets="$$tmpdir/packets.jsonl"; \
	tmp_summary="$$tmpdir/summary.json"; \
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli pilot-prepare \
	  --seed 20260812 \
	  --arms control treatment \
	  --cases "$$cases" \
	  --output "$$tmp_packets" \
	  --format jsonl; \
	if [ ! -f "$$expected_packets" ]; then \
	  echo "stage1-pilot-smoke: missing $$expected_packets"; \
	  exit 1; \
	fi; \
	cmp -s "$$tmp_packets" "$$expected_packets"; \
	echo "stage1-pilot-smoke: packets match $$expected_packets"; \
	if [ ! -f "$$responses" ]; then \
	  echo "stage1-pilot-smoke: missing $$responses"; \
	  exit 1; \
	fi; \
	if [ ! -f "$$annotations" ]; then \
	  echo "stage1-pilot-smoke: missing $$annotations"; \
	  exit 1; \
	fi; \
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli pilot-score \
	  --packets "$$expected_packets" \
	  --responses "$$responses" \
	  --annotations "$$annotations" \
	  --output "$$tmp_summary"; \
	if [ ! -f "$$expected_summary" ]; then \
	  echo "stage1-pilot-smoke: missing $$expected_summary"; \
	  exit 1; \
	fi; \
	cmp -s "$$tmp_summary" "$$expected_summary"; \
	echo "stage1-pilot-smoke: summary matches $$expected_summary"; \
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/pilot-packet.schema.json "$$expected_packets"; \
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/pilot-response.schema.json "$$responses"; \
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/pilot-annotation.schema.json "$$annotations"; \
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli validate --schema schemas/pilot-summary.schema.json "$$expected_summary"

lab00:
	$(MAKE) stage1-pilot-smoke
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli lab00 --output artifacts/lab00/index.html --open

lab00-render:
	$(MAKE) stage1-pilot-smoke
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli lab00 --output artifacts/lab00/index.html

lab:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli lab-suite --root . --output $(LAB_SUITE_OUTPUT) --open

lab-render:
	PYTHONPATH=$(PYTHONPATH) python3 -m latent_triz.cli lab-suite --root . --output $(LAB_SUITE_OUTPUT)
