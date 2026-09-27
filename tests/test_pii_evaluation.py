from pathlib import Path

from training.evaluate_pii import evaluate
from training.generate_pii_dataset import generate


ROOT = Path(__file__).resolve().parents[1]


def test_generated_pii_corpus_passes_rule_engine_gate():
    result = evaluate(generate(size=500, seed=42), ROOT / "config" / "pii_rules.yaml")
    assert result["precision"] >= 0.95
    assert result["recall"] >= 0.95
    assert result["release_passed"] is True
