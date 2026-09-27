# Current benchmark results

## Prompt-injection model v0.1.0

The pinned Deepset evaluation completed successfully, but the model is not approved for the public v0.2 deployment.

| Metric | Result | Gate |
|---|---:|---:|
| Precision | 96.2% | Reported |
| Recall | 85.0% | At least 90% |
| F1 | 90.3% | Reported |
| Standard benign FPR | 3.6% | Reported |
| Difficult-benign FPR | 4.0% | At most 5% |

The release workflow correctly left `hf_commit` empty. The full machine-readable result is in `benchmarks/model-v0.1-experimental.json`.

## Gateway overhead

The local loopback smoke benchmark measured 3.6 ms median and 4.7 ms p95 over 20 requests. This excludes Gemini generation and uses a synthetic smoke classifier; it validates application overhead rather than production capacity.

## PII engine v0.2.0

The deterministic engine achieved 100% exact-span precision and recall on 3,000 generated regression examples across Aadhaar, credit cards, email, PAN and Indian phone numbers. The corpus is generated from the same declared formats and checksum rules, so this validates implementation consistency rather than independent real-world generalization.
