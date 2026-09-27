from pathlib import Path

from app.schemas import Decision, PIIFinding
from app.services.policy import PolicyEngine


POLICY = Path(__file__).resolve().parents[1] / "config" / "policy.yaml"


def finding(entity: str) -> PIIFinding:
    return PIIFinding(entity_type=entity, start=0, end=4, confidence=0.99, validated=True)


def test_injection_has_highest_precedence():
    policy = PolicyEngine(POLICY)
    decision, reasons = policy.evaluate(0.99, [finding("EMAIL")], 0.82)
    assert decision == Decision.BLOCK
    assert reasons == ["PROMPT_INJECTION"]


def test_aadhaar_blocks_and_email_redacts():
    policy = PolicyEngine(POLICY)
    assert policy.evaluate(0.1, [finding("AADHAAR")], 0.82)[0] == Decision.BLOCK
    assert policy.evaluate(0.1, [finding("EMAIL")], 0.82)[0] == Decision.REDACT
    assert policy.evaluate(0.1, [], 0.82)[0] == Decision.ALLOW
