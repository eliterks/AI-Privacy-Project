from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from huggingface_hub import hf_hub_download
from skops.io import get_untrusted_types, load

from app.config import Settings
from app.schemas import InjectionResult


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class InjectionDetector:
    def __init__(self, model: Any, metadata: dict[str, Any], revision: str):
        self.model = model
        self.version = str(metadata.get("model_version", "unknown"))
        self.threshold = float(metadata.get("decision_threshold", 0.82))
        self.injection_label = str(metadata.get("injection_label", "1"))
        self.revision = revision

    @classmethod
    def from_settings(cls, settings: Settings) -> "InjectionDetector":
        settings.validate_model_source()
        if settings.model_path:
            model_path = Path(settings.model_path)
            metadata_path = model_path.with_name(settings.model_metadata_filename)
            revision = "local"
        else:
            assert settings.model_repo and settings.model_revision
            model_path = Path(
                hf_hub_download(
                    repo_id=settings.model_repo,
                    filename=settings.model_filename,
                    revision=settings.model_revision,
                )
            )
            metadata_path = Path(
                hf_hub_download(
                    repo_id=settings.model_repo,
                    filename=settings.model_metadata_filename,
                    revision=settings.model_revision,
                )
            )
            revision = settings.model_revision

        if not model_path.is_file() or not metadata_path.is_file():
            raise FileNotFoundError("Model artifact or metadata file is missing")
        if settings.model_sha256 and _sha256(model_path) != settings.model_sha256.lower():
            raise ValueError("Model checksum does not match MODEL_SHA256")

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        expected_hash = metadata.get("artifact_sha256")
        if expected_hash and _sha256(model_path) != str(expected_hash).lower():
            raise ValueError("Model checksum does not match metadata")

        unknown_types = get_untrusted_types(file=model_path)
        if unknown_types:
            raise ValueError(f"Model artifact contains unapproved types: {unknown_types}")
        model = load(model_path, trusted=[])
        return cls(model, metadata, revision)

    def predict(self, text: str, threshold: float | None = None) -> InjectionResult:
        probabilities = self.model.predict_proba([text])[0]
        classes = [str(value) for value in self.model.classes_]
        if self.injection_label not in classes:
            raise RuntimeError(f"Injection label {self.injection_label!r} not found in model classes")
        score = float(probabilities[classes.index(self.injection_label)])
        active_threshold = self.threshold if threshold is None else threshold
        return InjectionResult(
            label="injection" if score >= active_threshold else "benign",
            score=score,
            threshold=active_threshold,
            model_version=self.version,
        )
