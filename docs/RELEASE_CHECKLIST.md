# v0.2 release checklist

## Model

- Kaggle notebook output is saved publicly.
- `evaluation.json` passes both release gates.
- Model card contains measured metrics and known failures.
- Model artifact hash matches `metadata.json`.
- Hugging Face model commit or version tag is immutable.

## Application

- Python tests and React build pass.
- Docker image builds from a clean checkout.
- Local smoke test passes.
- `MODEL_REVISION` and `MODEL_SHA256` reference the approved artifact.
- `GEMINI_API_KEY` is a Space secret, never a variable or repository file.

## Public verification

- Benign, injection, PII and quoted-security examples are visible in the UI.
- `/version` displays the deployed versions.
- Blocked requests do not call Gemini.
- Raw prompts and model responses are not logged.
- Deployed Space smoke test passes.

