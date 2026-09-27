# Architecture and security boundaries

## Request lifecycle

1. FastAPI validates the text length and applies a per-process rate limit.
2. The injection model assigns an attack probability.
3. The PII engine identifies validated spans.
4. The policy engine returns `ALLOW`, `REDACT`, or `BLOCK`.
5. A blocked request terminates without invoking Gemini.
6. A redacted request sends only placeholders to Gemini.
7. The complete Gemini response is scanned before it is returned.

## Version boundaries

The gateway, injection artifact, PII rules, policy and evaluation dataset have independent versions. `/version` exposes all five plus the immutable model revision.

The policy uses the calibrated threshold stored in model metadata by default. A numeric `injection_threshold` in the policy file is an explicit, versioned override.

## Failure behavior

- Missing or invalid model: readiness fails and protected endpoints return 503.
- Artifact checksum mismatch: model loading fails.
- Gemini timeout, quota or authentication error: generation returns 502.
- Sensitive Gemini output: redacted; output containing blocked PII is replaced by a policy message.
- The public service does not persist prompts, findings, or responses.

## v0.2 boundary

The version intentionally excludes persistent audit storage, user accounts, distributed workers, Kubernetes, document ingestion and agent tool authorization.
