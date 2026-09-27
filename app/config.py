from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    gateway_version: str = os.getenv("GATEWAY_VERSION", "0.2.0")
    evaluation_version: str = os.getenv("EVALUATION_VERSION", "0.1.0")
    model_repo: str | None = os.getenv("MODEL_REPO")
    model_revision: str | None = os.getenv("MODEL_REVISION")
    model_filename: str = os.getenv("MODEL_FILENAME", "model.skops")
    model_path: str | None = os.getenv("MODEL_PATH")
    model_sha256: str | None = os.getenv("MODEL_SHA256")
    model_metadata_filename: str = os.getenv("MODEL_METADATA_FILENAME", "metadata.json")
    policy_path: Path = Path(os.getenv("POLICY_PATH", BASE_DIR / "config" / "policy.yaml"))
    pii_rules_path: Path = Path(os.getenv("PII_RULES_PATH", BASE_DIR / "config" / "pii_rules.yaml"))
    static_dir: Path = Path(os.getenv("STATIC_DIR", BASE_DIR / "static"))
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    gemini_timeout_seconds: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))
    max_input_characters: int = int(os.getenv("MAX_INPUT_CHARACTERS", "5000"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    def validate_model_source(self) -> None:
        if self.model_path:
            return
        if not self.model_repo or not self.model_revision:
            raise ValueError("Set MODEL_PATH, or both MODEL_REPO and MODEL_REVISION")
        if self.model_revision in {"main", "master", "latest"}:
            raise ValueError("MODEL_REVISION must be an immutable commit hash or release tag")

