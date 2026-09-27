from __future__ import annotations

from pathlib import Path

import yaml

from app.schemas import Decision, PIIFinding


class PolicyEngine:
    def __init__(self, policy_path: Path):
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        self.version = str(policy["version"])
        configured_threshold = policy.get("injection_threshold", "model")
        self.injection_threshold = None if configured_threshold == "model" else float(configured_threshold)
        self.block_entities = set(policy["rules"]["block_entities"])
        self.redact_entities = set(policy["rules"]["redact_entities"])

    def evaluate(
        self,
        injection_score: float,
        findings: list[PIIFinding],
        injection_threshold: float | None = None,
    ) -> tuple[Decision, list[str]]:
        threshold = self.injection_threshold if self.injection_threshold is not None else injection_threshold
        if threshold is None:
            raise ValueError("A model or policy injection threshold is required")
        if injection_score >= threshold:
            return Decision.BLOCK, ["PROMPT_INJECTION"]

        entity_types = {item.entity_type for item in findings}
        blocked = sorted(entity_types & self.block_entities)
        if blocked:
            return Decision.BLOCK, [f"BLOCKED_PII:{name}" for name in blocked]

        redact = sorted(entity_types & self.redact_entities)
        if redact:
            return Decision.REDACT, [f"REDACTED_PII:{name}" for name in redact]

        return Decision.ALLOW, ["NO_POLICY_VIOLATION"]
