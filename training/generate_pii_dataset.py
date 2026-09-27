from __future__ import annotations

import argparse
import json
import random
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pii import _VERHOEFF_D, _VERHOEFF_P, is_valid_verhoeff


_VERHOEFF_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def verhoeff_check_digit(prefix: str) -> str:
    checksum = 0
    for index, digit in enumerate(reversed(prefix)):
        checksum = _VERHOEFF_D[checksum][_VERHOEFF_P[(index + 1) % 8][int(digit)]]
    return str(_VERHOEFF_INV[checksum])


def luhn_check_digit(prefix: str) -> str:
    for candidate in string.digits:
        digits = prefix + candidate
        total = 0
        parity = len(digits) % 2
        for index, digit in enumerate(map(int, digits)):
            if index % 2 == parity:
                digit = digit * 2 - 9 if digit * 2 > 9 else digit * 2
            total += digit
        if total % 10 == 0:
            return candidate
    raise RuntimeError("Unable to construct Luhn number")


def span_example(prefix: str, value: str, suffix: str, entity: str) -> dict:
    return {
        "text": prefix + value + suffix,
        "entities": [{"type": entity, "start": len(prefix), "end": len(prefix) + len(value)}],
        "synthetic": True,
    }


def generate(size: int = 3000, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    positives = int(size * 0.60)
    clean_count = int(size * 0.25)
    rows: list[dict] = []
    entities = ("EMAIL", "PHONE_IN", "PAN", "AADHAAR", "CREDIT_CARD")
    for index in range(positives):
        entity = entities[index % len(entities)]
        if entity == "EMAIL":
            value = f"sample.user{index}@example.test"
        elif entity == "PHONE_IN":
            value = f"+91 {rng.choice('6789')}{rng.randrange(10**9):09d}"
        elif entity == "PAN":
            value = "".join(rng.choices(string.ascii_uppercase, k=5)) + f"{rng.randrange(10000):04d}" + rng.choice(string.ascii_uppercase)
        elif entity == "AADHAAR":
            prefix = rng.choice("23456789") + f"{rng.randrange(10**10):010d}"
            raw = prefix + verhoeff_check_digit(prefix)
            value = f"{raw[:4]} {raw[4:8]} {raw[8:]}"
        else:
            prefix = "4" + f"{rng.randrange(10**14):014d}"
            value = prefix + luhn_check_digit(prefix)
        rows.append(span_example("Synthetic test value: ", value, ".", entity))

    clean_templates = [
        "Summarize the quarterly report without including private information.",
        "Explain how checksum validation reduces false positive matches.",
        "The order reference is {number} and is not a phone number.",
        "The years {a}, {b}, and {c} appear in the forecast.",
    ]
    for index in range(clean_count):
        template = clean_templates[index % len(clean_templates)]
        rows.append({"text": template.format(number=rng.randrange(10**9), a=2024, b=2025, c=2026), "entities": [], "synthetic": True})

    while len(rows) < size:
        invalid = f"{rng.randrange(1000, 9999)} {rng.randrange(1000, 9999)} {rng.randrange(1000, 9999)}"
        while is_valid_verhoeff(invalid):
            invalid = invalid[:-1] + str((int(invalid[-1]) + 1) % 10)
        rows.append({"text": f"Reference sequence {invalid} is intentionally invalid.", "entities": [], "synthetic": True})
    rng.shuffle(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="/kaggle/working/pii_synthetic_v0.1.jsonl")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in generate(args.size, args.seed):
            handle.write(json.dumps(row) + "\n")
    print(f"Wrote {args.size} synthetic records to {output}")


if __name__ == "__main__":
    main()
