---
title: AI Security Gateway
emoji: 🛡️
colorFrom: teal
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
---

# AI Security Gateway v0.2

A portfolio-ready security gateway that inspects text before it reaches an LLM. It combines a versioned prompt-injection classifier, deterministic PII detection, explicit policy decisions, Gemini generation, and output privacy checks.

## What is implemented

- FastAPI endpoints for analysis, protected generation, readiness, health, and versions.
- TF-IDF + Logistic Regression training on Kaggle with local MLflow tracking.
- Email, Indian phone, PAN, Aadhaar and credit-card detection and redaction.
- Verhoeff validation for Aadhaar and Luhn validation for credit cards.
- React playground compiled into the same Docker image as the API.
- Pinned Hugging Face model revisions with optional SHA-256 verification.
- Fail-closed startup, input limits, request rate limiting, and no raw-prompt persistence.

## Architecture

```text
React UI
   │
   ▼
FastAPI Gateway
   ├── Injection detector
   ├── PII detector/redactor
   ├── Policy engine
   └── Gemini adapter
            │
            ▼
      Output PII check
```

Blocked text is never sent to Gemini. Redacted text is the only version sent for `REDACT` decisions.

## 1. Train on Kaggle

1. Create a Kaggle dataset from this repository and name it `ai-security-gateway-source`.
2. Import [training/kaggle_training.ipynb](training/kaggle_training.ipynb) as a Kaggle notebook.
3. Enable Internet so the notebook can download `deepset/prompt-injections`.
4. Set `HF_MODEL_REPO` in the configuration cell.
5. Add `HF_TOKEN` through Kaggle Secrets if the passing artifact should be published.
6. Run all cells and save a notebook version with outputs.

The notebook produces:

```text
/kaggle/working/release/
├── model.skops
├── metadata.json
├── evaluation.json
├── dataset_manifest.json
└── requirements.txt

/kaggle/working/mlruns.zip
```

The upload runs only when recall is at least 90%, difficult-benign FPR is at most 5%, and both Hugging Face secrets are configured.

Copy [MODEL_CARD.md](MODEL_CARD.md) into the Hugging Face model repository and update it with the published evaluation values.

## 2. Run locally

Download `model.skops` and `metadata.json` from the approved Hugging Face release into `artifacts/`. Copy `.env.example` to `.env`, set `GEMINI_API_KEY`, and run:

```bash
docker compose up --build
```

Open `http://localhost:7860`. API documentation is at `http://localhost:7860/docs`.

Run the deployed smoke test:

```bash
python scripts/smoke_test.py --base-url http://localhost:7860
```

## 3. Deploy to Hugging Face Spaces

Create a public Docker Space and push the repository contents to it. Configure:

| Name | Space setting | Value |
|---|---|---|
| `MODEL_REPO` | Variable | Public Hugging Face model repository |
| `MODEL_REVISION` | Variable | Exact approved commit hash or version tag |
| `MODEL_SHA256` | Variable | SHA-256 from `metadata.json` |
| `GEMINI_MODEL` | Variable | `gemini-3.8-flash` |
| `GEMINI_API_KEY` | Secret | Gemini API key |

Do not set `MODEL_PATH` in the Space. The gateway downloads the pinned model and metadata from the model repository during startup. `/ready` remains unavailable if loading or checksum validation fails.

After the Space builds, run:

```bash
python scripts/smoke_test.py --base-url https://YOUR-SPACE.hf.space
```

## API

### Analyze

```http
POST /api/v1/analyze
Content-Type: application/json

{"text":"Email the report to student@example.com"}
```

### Generate

```http
POST /api/v1/generate
Content-Type: application/json

{"text":"Explain encryption"}
```

Supporting endpoints are `/health`, `/ready`, and `/version`.

## Development

```bash
python -m venv .venv
pip install -r requirements-dev.txt
pytest -q

cd frontend
npm ci
npm run build
```

## Portfolio links

Replace these after publishing:

- Live demo: `https://huggingface.co/spaces/YOUR_HF_USERNAME/ai-security-gateway`
- Model: `https://huggingface.co/YOUR_HF_USERNAME/prompt-injection-guard-v1`
- Kaggle notebook: `https://www.kaggle.com/code/YOUR_KAGGLE_USERNAME/...`
- Source and benchmarks: this repository

The latest measured results are documented in [docs/BENCHMARK_RESULTS.md](docs/BENCHMARK_RESULTS.md). The current injection artifact is experimental because it has not yet met the 90% recall release gate.

## Project documentation

- [Student build roadmap](docs/STUDENT_BUILD_ROADMAP.md): a teaching sequence from architecture and data through training, testing, and public v0.2 deployment.
- [Current implementation status](docs/CURRENT_IMPLEMENTATION_STATUS.md): what is complete, what has been verified, and what remains before v0.2 can be declared released.
- [Architecture and security boundaries](docs/ARCHITECTURE.md)
- [Benchmark results](docs/BENCHMARK_RESULTS.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)

## Limitations

This v0.2 detector uses a small, primarily English dataset. It does not guarantee protection against adaptive, multilingual, indirect, or multi-turn attacks. The public demo is stateless and must only receive synthetic data.
