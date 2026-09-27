from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.schemas import PIIFinding


_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def is_valid_verhoeff(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 12 or digits[0] in "01":
        return False
    checksum = 0
    for index, digit in enumerate(reversed(digits)):
        checksum = _VERHOEFF_D[checksum][_VERHOEFF_P[index % 8][int(digit)]]
    return checksum == 0


def is_valid_luhn(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    total = 0
    parity = len(digits) % 2
    for index, digit in enumerate(map(int, digits)):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


@dataclass(frozen=True)
class _Candidate:
    entity_type: str
    start: int
    end: int
    confidence: float
    validated: bool
    priority: int


class PIIEngine:
    _patterns = {
        "EMAIL": re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w-])", re.I),
        "PHONE_IN": re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"),
        "PAN": re.compile(r"(?<![A-Z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Z0-9])"),
        "AADHAAR": re.compile(r"(?<!\d)[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?!\d)"),
        "CREDIT_CARD": re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"),
    }
    _priorities = {"AADHAAR": 50, "CREDIT_CARD": 40, "PAN": 30, "EMAIL": 20, "PHONE_IN": 10}

    def __init__(self, rules_path: Path):
        rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        self.version = str(rules["version"])
        self.replacements = {
            name: str(value["replacement"]) for name, value in rules["entities"].items()
        }

    def detect(self, text: str) -> list[PIIFinding]:
        candidates: list[_Candidate] = []
        for entity_type, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                validated = True
                confidence = 0.99
                if entity_type == "AADHAAR":
                    validated = is_valid_verhoeff(match.group())
                elif entity_type == "CREDIT_CARD":
                    validated = is_valid_luhn(match.group())
                if not validated:
                    continue
                candidates.append(
                    _Candidate(
                        entity_type,
                        match.start(),
                        match.end(),
                        confidence,
                        validated,
                        self._priorities[entity_type],
                    )
                )

        selected: list[_Candidate] = []
        for candidate in sorted(candidates, key=lambda item: (-item.priority, item.start, -item.end)):
            if any(candidate.start < other.end and other.start < candidate.end for other in selected):
                continue
            selected.append(candidate)

        return [
            PIIFinding(
                entity_type=item.entity_type,
                start=item.start,
                end=item.end,
                confidence=item.confidence,
                validated=item.validated,
            )
            for item in sorted(selected, key=lambda item: item.start)
        ]

    def redact(self, text: str, findings: list[PIIFinding]) -> str:
        counts: dict[str, int] = {}
        chunks: list[str] = []
        cursor = 0
        for finding in sorted(findings, key=lambda item: item.start):
            counts[finding.entity_type] = counts.get(finding.entity_type, 0) + 1
            label = self.replacements.get(finding.entity_type, finding.entity_type)
            replacement = f"[{label}_{counts[finding.entity_type]}]"
            chunks.extend((text[cursor:finding.start], replacement))
            cursor = finding.end
        chunks.append(text[cursor:])
        return "".join(chunks)
