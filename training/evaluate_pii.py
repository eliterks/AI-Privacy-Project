from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from app.services.pii import PIIEngine


def evaluate(rows: list[dict], rules_path: Path) -> dict:
    engine = PIIEngine(rules_path)
    totals = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for row in rows:
        expected = {(item["type"], item["start"], item["end"]) for item in row["entities"]}
        predicted = {(item.entity_type, item.start, item.end) for item in engine.detect(row["text"])}
        for entity in expected & predicted:
            totals[entity[0]]["tp"] += 1
        for entity in predicted - expected:
            totals[entity[0]]["fp"] += 1
        for entity in expected - predicted:
            totals[entity[0]]["fn"] += 1

    by_entity = {}
    aggregate = {"tp": 0, "fp": 0, "fn": 0}
    for entity, counts in sorted(totals.items()):
        for key in aggregate:
            aggregate[key] += counts[key]
        precision = counts["tp"] / max(1, counts["tp"] + counts["fp"])
        recall = counts["tp"] / max(1, counts["tp"] + counts["fn"])
        by_entity[entity] = {**counts, "precision": precision, "recall": recall}

    precision = aggregate["tp"] / max(1, aggregate["tp"] + aggregate["fp"])
    recall = aggregate["tp"] / max(1, aggregate["tp"] + aggregate["fn"])
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    release_passed = all(
        values["precision"] >= 0.95 and values["recall"] >= 0.95
        for values in by_entity.values()
    )
    return {
        "engine_version": engine.version,
        "examples": len(rows),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "by_entity": by_entity,
        "release_passed": release_passed,
    }


def write_evaluation(rows: list[dict], rules_path: Path, output_path: Path) -> dict:
    result = evaluate(rows, rules_path)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

