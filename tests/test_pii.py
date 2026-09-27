from pathlib import Path

from app.services.pii import PIIEngine, is_valid_luhn, is_valid_verhoeff
from training.generate_pii_dataset import verhoeff_check_digit


RULES = Path(__file__).resolve().parents[1] / "config" / "pii_rules.yaml"


def valid_aadhaar() -> str:
    prefix = "23456789012"
    raw = prefix + verhoeff_check_digit(prefix)
    return f"{raw[:4]} {raw[4:8]} {raw[8:]}"


def test_checksum_validators():
    assert is_valid_verhoeff(valid_aadhaar())
    assert not is_valid_verhoeff("2345 6789 0123")
    assert is_valid_luhn("4111111111111111")
    assert not is_valid_luhn("4111111111111112")


def test_detects_and_redacts_supported_pii():
    engine = PIIEngine(RULES)
    text = "Email student@example.com, PAN ABCDE1234F, card 4111111111111111."
    findings = engine.detect(text)
    assert [item.entity_type for item in findings] == ["EMAIL", "PAN", "CREDIT_CARD"]
    redacted = engine.redact(text, findings)
    assert "student@example.com" not in redacted
    assert "ABCDE1234F" not in redacted
    assert "4111111111111111" not in redacted
    assert "[EMAIL_1]" in redacted


def test_invalid_structured_identifiers_are_not_pii():
    engine = PIIEngine(RULES)
    findings = engine.detect("References 2345 6789 0123 and 4111111111111112 are invalid.")
    assert findings == []


def test_aadhaar_has_priority_over_other_numeric_patterns():
    engine = PIIEngine(RULES)
    value = valid_aadhaar()
    findings = engine.detect(f"Synthetic Aadhaar {value}")
    assert len(findings) == 1
    assert findings[0].entity_type == "AADHAAR"

