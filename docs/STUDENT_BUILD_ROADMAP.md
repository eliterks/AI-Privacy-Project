# Student build roadmap: AI Security Gateway v0.1 to v0.2

## 1. What the student is building

The project is a small security gateway placed between a user and a large language model (LLM). It answers two questions before any prompt reaches Gemini:

1. Does the prompt look like a prompt-injection attempt?
2. Does the prompt contain personally identifiable information (PII)?

The gateway then applies a fixed policy:

```text
Injection score at or above threshold  -> BLOCK
Validated Aadhaar                     -> BLOCK
Email, phone, PAN, or credit card     -> REDACT
No finding                            -> ALLOW
Required detector unavailable         -> NOT READY
```

An allowed prompt is sent unchanged to Gemini. A redacted prompt is sent only after sensitive spans have been replaced. A blocked prompt never reaches Gemini. The generated response is scanned again before it is displayed.

This project contains one trained model and one deterministic detector. The prompt-injection component is a TF-IDF plus Logistic Regression model. The PII component uses regular expressions and checksum validation; it is not a second machine-learning model.

## 2. Target architecture

```text
Kaggle notebook
  |- Deepset prompt-injection data
  |- difficult-benign additions
  |- scikit-learn training
  |- MLflow experiment records
  `- model.skops + metadata + evaluation
              |
              v
Hugging Face model repository (immutable revision)
              |
              v
React UI -> FastAPI gateway
              |- prompt-injection detector
              |- PII detector and redactor
              |- versioned policy
              |- Gemini adapter
              `- output PII inspection
                         |
                         v
              Hugging Face Docker Space
```

The single-container design is intentional for v0.2. It is easier to understand, run, review, and deploy than a distributed architecture. A database, message queue, Kubernetes, user accounts, and persistent prompt logs are outside this version.

## 3. Learning outcomes

By the end, a student should be able to:

- explain why prompt injection and PII require different detection methods;
- prepare text-classification data without train/test leakage;
- train, calibrate, evaluate, and safely serialize a small classifier;
- use MLflow to make a training run reproducible;
- implement exact-span PII redaction and checksum validation;
- convert detector findings into deterministic policy decisions;
- build a fail-closed FastAPI service around a model;
- call an external LLM only after policy approval;
- scan LLM output before returning it;
- compile a React UI and serve it from the API container;
- pin model revisions and verify artifact checksums; and
- distinguish local verification from a real public deployment.

## 4. Prerequisites and tools

The student needs basic Python, HTTP, JSON, Git, and React knowledge. Advanced deep-learning knowledge is unnecessary for v0.2.

Use these services and tools:

| Purpose | Tool |
|---|---|
| Source control | Git and GitHub |
| Model training | Kaggle Notebook |
| Experiment tracking | MLflow inside Kaggle |
| Model registry | Hugging Face model repository |
| Public application | Hugging Face Docker Space |
| API | FastAPI and Uvicorn |
| UI | React and Vite |
| LLM | Google Gemini API |
| Packaging | Docker and Docker Compose |
| Tests | pytest and GitHub Actions |

Secrets belong in Kaggle Secrets or Hugging Face Space Secrets. They must never be committed to Git.

## 5. Version plan

| Version | Student outcome | Release evidence |
|---|---|---|
| `v0.0` | API contracts and project skeleton | Health endpoint and placeholder tests |
| `v0.1-pii` | PII detection, validation, and redaction | Exact-span tests and synthetic evaluation |
| `v0.1-model` | Reproducible prompt-injection classifier | MLflow run and release artifacts |
| `v0.1-gateway` | Detectors combined through policy | Analyze endpoint and downstream-call tests |
| `v0.2-rc` | UI, Gemini path, Docker, and CI | Local build, tests, benchmark, smoke test |
| `v0.2.0` | Public, reproducible portfolio release | Four public links and deployed smoke test |

Do not promote a version because its code exists. Promote it only when its release gate and evidence both pass.

## 6. Suggested teaching schedule

The roadmap fits eight guided sessions plus independent release work. A session may be expanded into a week for beginners.

### Session 1: threat model, scope, and contracts

**Teach**

- Prompt injection is untrusted text attempting to change system behavior.
- PII detection finds sensitive spans; it does not decide policy by itself.
- Detection, policy, and action should remain separate components.
- A security service must fail closed when a required detector cannot load.

**Build**

1. Draw the request lifecycle.
2. Define `ALLOW`, `REDACT`, and `BLOCK`.
3. Define the request and response schemas.
4. Create `/health`, `/ready`, and `/version` contracts.
5. Limit input to 5,000 characters.

**Checkpoint**

The student can explain why `/health` may return 200 while `/ready` returns 503, and why a blocked prompt must cause zero Gemini calls.

### Session 2: deterministic PII engine

**Teach**

- Regular expressions produce candidate spans.
- Format matching alone is insufficient for structured identifiers.
- Luhn validates credit-card candidates; Verhoeff validates Aadhaar candidates.
- Span offsets must refer to the original text.
- Overlapping candidates need a stable priority rule.

**Build**

1. Add patterns for email, Indian phone, PAN, Aadhaar, and credit card.
2. Reject invalid Aadhaar and card checksums.
3. Give Aadhaar higher overlap priority than generic numeric patterns.
4. Replace matches from their recorded spans with typed placeholders such as `[EMAIL_1]`.
5. Keep policy actions in YAML rather than embedding them in the detector.

**Checkpoint**

- Valid identifiers are detected.
- Invalid checksum examples are ignored.
- Multiple entities are redacted without changing unrelated characters.
- Original PII does not appear in the sanitized result.

Relevant code: `app/services/pii.py`, `config/pii_rules.yaml`, and `tests/test_pii.py`.

### Session 3: PII evaluation data

**Teach**

- A generated regression corpus proves implementation consistency.
- It does not prove real-world generalization when generation and detection use the same rules.
- Precision, recall, and exact-span matching answer different questions from simple pattern coverage.

**Build**

1. Generate 2,000-5,000 positive, clean, and ambiguous examples.
2. Store expected entity type and character offsets.
3. Evaluate predicted spans against exact expected spans.
4. Report aggregate and per-entity failures.
5. Add hand-written boundary cases from a separate reviewer before claiming real-world quality.

**Checkpoint**

Run:

```bash
python training/generate_pii_dataset.py --size 3000 --output artifacts/pii_synthetic_v0.1.jsonl
pytest -q tests/test_pii_evaluation.py
```

The included generated regression suite should pass, while the report must retain its synthetic-data limitation.

### Session 4: prompt-injection data and leakage control

**Teach**

- Use `deepset/prompt-injections` as the base dataset.
- Preserve the supplied test split as held-out evidence.
- Exact and near duplicates can inflate evaluation results.
- Difficult-benign prompts discuss attacks without performing them and are essential for measuring false positives.

**Build in Kaggle**

1. Import `training/kaggle_training.ipynb`.
2. Enable Internet access for Hugging Face dataset download.
3. Pin Python package versions from `training/requirements-kaggle.txt`.
4. Normalize labels and text.
5. Remove train examples that duplicate test text.
6. Add 300-500 reviewed difficult-benign examples.
7. Record source revision, hashes, row counts, and random seed.

**Checkpoint**

The exported `dataset_manifest.json` identifies the source revision and confirms leakage removal. A student should be able to reconstruct which data produced a model without guessing.

### Session 5: model training, threshold selection, and MLflow

**Teach**

- TF-IDF converts text into sparse lexical features.
- Logistic Regression is fast, interpretable, CPU-friendly, and appropriate for this small v0.2 baseline.
- The default probability cutoff is not automatically the correct security threshold.
- Select the threshold on validation data and evaluate it once on test data.
- Recall and difficult-benign false-positive rate are the primary gates; accuracy alone can hide the wrong tradeoff.

**Build in Kaggle**

1. Train a TF-IDF plus Logistic Regression pipeline with seed 42.
2. Search validation thresholds for a useful recall/FPR tradeoff.
3. Log parameters, metrics, confusion matrix, threshold, and artifacts to MLflow.
4. Export with `skops` rather than a general-purpose pickle.
5. Reload the artifact and confirm prediction parity.
6. Produce `model.skops`, `metadata.json`, `evaluation.json`, `dataset_manifest.json`, and `requirements.txt`.
7. Zip `/kaggle/working/mlruns` as notebook output.

**Release gate**

```text
Held-out injection recall >= 90%
Difficult-benign FPR      <= 5%
No train/test duplicates
Reloaded predictions match
Dataset and code versions recorded
```

If either metric misses the gate, label the run experimental. Improve data coverage or features, retrain, and retain the failed run for comparison. Never lower the gate after seeing test results simply to publish the artifact.

Relevant code: `training/train.py` and `training/kaggle_training.ipynb`.

### Session 6: policy and secure request flow

**Teach**

- Detectors produce signals; policy converts signals into actions.
- Precedence removes ambiguity when multiple findings occur.
- Sanitization must happen before the downstream call.
- Output inspection is required because an LLM may generate PII even from a clean prompt.

**Build**

1. Load the classifier from a local artifact during development.
2. In deployment, download it from an exact Hugging Face revision.
3. Verify its SHA-256 checksum and reject unapproved serialized types.
4. Run injection and PII analysis.
5. Apply injection, Aadhaar, redactable-PII, and allow rules in that order.
6. Return the decision, reasons, spans, sanitized text, threshold, score, and component versions.
7. For generation, call Gemini only for `ALLOW` or `REDACT`.
8. Inspect and sanitize the generated output.

**Checkpoint**

Tests must prove:

- an injection block produces zero downstream calls;
- Gemini receives only sanitized input after a `REDACT` decision;
- output email or phone data is redacted;
- blocked output PII is not returned; and
- a missing model leaves the service not ready.

Relevant code: `app/gateway.py`, `app/services/policy.py`, and `tests/test_gateway.py`.

### Session 7: API and React demonstration

**Teach**

- The UI should reveal the security decision, not hide it behind a chat box.
- A portfolio reviewer needs examples, versions, scores, spans, and failure states.
- Serving compiled UI assets from FastAPI avoids cross-origin setup for this version.

**Build**

1. Implement `POST /api/v1/analyze` and `POST /api/v1/generate`.
2. Add controlled 422, 429, 502, and 503 responses.
3. Add prepared benign, injection, and PII examples.
4. Display the score and selected threshold.
5. Highlight detected entities and compare original with sanitized text.
6. Display the safe Gemini response and all component versions.
7. Warn users not to submit real confidential or personal data.

**Checkpoint**

```bash
pytest -q
cd frontend
npm ci
npm run build
```

The UI build must succeed and API tests must pass before container work begins.

### Session 8: packaging, deployment, and public proof

**Teach**

- A Docker image packages the runtime, but it does not contain secrets.
- A model tag is convenient; an immutable commit plus checksum is stronger evidence.
- Readiness should fail if the required model cannot be loaded.
- A public portfolio claim needs a live test, not only deployment configuration.

**Build locally**

1. Put an approved `model.skops` and `metadata.json` in `artifacts/`.
2. Copy `.env.example` to `.env` and add only local secret values.
3. Build and run:

```bash
docker compose up --build
```

4. Open `http://localhost:7860` and `http://localhost:7860/docs`.
5. Run:

```bash
python scripts/smoke_test.py --base-url http://localhost:7860
```

**Publish the model**

1. Set `HF_MODEL_REPO` in Kaggle.
2. Add `HF_TOKEN` through Kaggle Secrets.
3. Allow the notebook to upload only a gate-passing artifact.
4. Record the returned Hugging Face commit hash.
5. Complete the model card with measured results and known failures.

**Publish the application**

1. Create a public Hugging Face Docker Space.
2. Copy or mirror the application repository into the Space.
3. Add `MODEL_REPO`, immutable `MODEL_REVISION`, `MODEL_SHA256`, and `GEMINI_MODEL` as variables.
4. Add `GEMINI_API_KEY` as a secret.
5. Confirm `/ready`, `/version`, analyze, redact, block, and generate behavior.
6. Run the smoke test against the public Space URL.

## 7. Student verification checklist

Use this order so failures are easy to locate:

1. **Unit tests:** regex boundaries, checksums, redaction spans, and policy precedence.
2. **Service tests:** readiness, input limits, controlled Gemini errors, and zero calls on block.
3. **Model evaluation:** held-out recall, F1, ROC-AUC, benign FPR, and difficult-benign FPR.
4. **Artifact test:** reload the exported model and compare predictions.
5. **Frontend build:** compile React from a clean dependency install.
6. **Container build:** build from a clean checkout.
7. **Local smoke test:** exercise the running HTTP service.
8. **Deployment smoke test:** repeat against the public Space.

Record the exact command, code commit, model revision, dataset version, environment, and result for every release claim.

## 8. Debugging guide

| Symptom | Likely cause | First check |
|---|---|---|
| `/ready` returns 503 | Model or metadata failed to load | Startup error and artifact paths |
| Checksum mismatch | Wrong model revision or stale hash | `MODEL_REVISION`, `MODEL_SHA256`, metadata hash |
| Too many benign prompts blocked | Threshold/data problem | Difficult-benign FPR and examples |
| Attacks pass through | Recall/data coverage problem | False negatives by attack family |
| Valid Aadhaar is missed | Invalid test number or formatting | Verhoeff result and span boundaries |
| Card-like number is ignored | Luhn failure | Digits and check digit |
| Gemini receives PII | Policy or redaction integration bug | Downstream-call mock assertion |
| Analyze works but Generate fails | Missing key, quota, or timeout | `GEMINI_API_KEY` and 502 detail |
| Space starts without UI | React assets not copied | Docker frontend stage and `/static` contents |

## 9. Portfolio evidence for v0.2.0

The README should contain four working links:

1. public Hugging Face Docker Space;
2. public Hugging Face model repository and model card;
3. public Kaggle notebook with saved outputs; and
4. GitHub source with benchmark results.

The reviewer should be able to verify the deployed component versions through `/version`, reproduce the container locally, inspect a passing model evaluation, and observe that blocked text never reaches Gemini.

## 10. What comes after v0.2

Extend only after the v0.2 evidence is complete:

- `v0.3`: independently reviewed adversarial and multilingual evaluation sets;
- `v0.4`: stronger classifier or small transformer compared against the TF-IDF baseline;
- `v0.5`: indirect-injection tests for retrieved documents and tool output;
- `v0.6`: persistent, privacy-safe aggregate observability and drift monitoring; and
- `v1.0`: authenticated tenants, auditable policy configuration, scalable rate limiting, and production operations.

Every later version should retain the v0.2 baseline so added complexity must show a measurable gain in recall, false-positive rate, latency, or operational reliability.
