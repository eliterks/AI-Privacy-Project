from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
from datasets import load_dataset
from huggingface_hub import HfApi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.pipeline import FeatureUnion
from sklearn.metrics.pairwise import cosine_similarity
from skops.io import dump, get_untrusted_types, load


SEED = 42
MODEL_VERSION = "0.1.0"
DATASET_REVISION = "4f61ecb038e9c3fb77e21034b22511b523772cdd"


def canonical(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_rows(texts: list[str], labels: list[int]) -> str:
    digest = hashlib.sha256()
    for text, label in sorted(zip(texts, labels), key=lambda row: (canonical(row[0]), row[1])):
        digest.update(f"{label}\t{canonical(text)}\n".encode())
    return digest.hexdigest()


def make_hard_benign(count: int = 400) -> list[str]:
    phrases = [
        "ignore previous instructions", "reveal the system prompt", "administrator access",
        "override the policy", "hidden instructions", "prompt injection", "jailbreak prompt",
        "system message", "password extraction", "instruction hierarchy",
    ]
    contexts = [
        "security training", "a university lecture", "a code review", "an audit report",
        "a threat-model workshop", "a policy document", "a research abstract", "a support article",
        "an interview question", "a defensive test plan",
    ]
    frames = [
        "Explain why the phrase '{phrase}' appears in {context}.",
        "Summarize a paragraph from {context} that discusses '{phrase}'.",
        "Write a safe example for {context} containing the quoted words '{phrase}'.",
        "Translate '{phrase}' while explaining that it must not be executed; this is for {context}.",
    ]
    rows = [frame.format(phrase=phrase, context=context) for frame in frames for context in contexts for phrase in phrases]
    return rows[:count]


def remove_train_test_leakage(train_texts: list[str], train_labels: list[int], test_texts: list[str]) -> tuple[list[str], list[int]]:
    test_norm = [canonical(text) for text in test_texts]
    seen: set[str] = set()
    unique_texts: list[str] = []
    unique_labels: list[int] = []
    for text, label in zip(train_texts, train_labels):
        normalized = canonical(text)
        if not normalized or normalized in seen or normalized in test_norm:
            continue
        seen.add(normalized)
        unique_texts.append(text)
        unique_labels.append(int(label))

    deduper = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
    matrix = deduper.fit_transform(test_norm + [canonical(text) for text in unique_texts])
    test_matrix = matrix[: len(test_norm)]
    train_matrix = matrix[len(test_norm) :]
    similarities = cosine_similarity(train_matrix, test_matrix, dense_output=False)
    max_similarity = np.asarray(similarities.max(axis=1).toarray()).ravel()
    keep = max_similarity < 0.95
    return (
        [text for text, retain in zip(unique_texts, keep) if retain],
        [label for label, retain in zip(unique_labels, keep) if retain],
    )


def select_threshold(y_true: np.ndarray, scores: np.ndarray, max_fpr: float = 0.05) -> float:
    candidates: list[tuple[float, float, float]] = []
    for threshold in np.linspace(0.05, 0.95, 181):
        predictions = (scores >= threshold).astype(int)
        benign = y_true == 0
        attacks = y_true == 1
        fpr = float(predictions[benign].mean()) if benign.any() else 0.0
        recall = float(predictions[attacks].mean()) if attacks.any() else 0.0
        candidates.append((float(threshold), recall, fpr))
    eligible = [row for row in candidates if row[2] <= max_fpr]
    if eligible:
        return max(eligible, key=lambda row: (row[1], -row[2], -row[0]))[0]
    return max(candidates, key=lambda row: (row[1] - row[2], row[1]))[0]


def calculate_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, float | list[list[int]]]:
    predictions = (scores >= threshold).astype(int)
    benign = y_true == 0
    result: dict[str, float | list[list[int]]] = {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "benign_fpr": float(predictions[benign].mean()) if benign.any() else 0.0,
        "confusion_matrix": confusion_matrix(y_true, predictions, labels=[0, 1]).tolist(),
    }
    return result


@dataclass
class TrainingResult:
    output_dir: str
    release_passed: bool
    model_version: str
    threshold: float
    metrics: dict
    hf_commit: str | None = None


def run_training(output_dir: str = "/kaggle/working/release", upload: bool = True) -> TrainingResult:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    mlruns = Path(os.getenv("MLFLOW_DIR", "/kaggle/working/mlruns"))
    mlruns.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(mlruns.resolve().as_uri())
    mlflow.set_experiment("prompt-injection-v0.1")

    dataset = load_dataset("deepset/prompt-injections", revision=DATASET_REVISION)
    train_texts = list(dataset["train"]["text"])
    train_labels = [int(value) for value in dataset["train"]["label"]]
    test_texts = list(dataset["test"]["text"])
    test_labels = [int(value) for value in dataset["test"]["label"]]

    hard_benign = make_hard_benign(400)
    hard_train, hard_validation, hard_test = hard_benign[:250], hard_benign[250:300], hard_benign[300:]
    train_texts.extend(hard_train)
    train_labels.extend([0] * len(hard_train))
    train_texts, train_labels = remove_train_test_leakage(train_texts, train_labels, test_texts + hard_test)

    fit_texts, validation_texts, fit_labels, validation_labels = train_test_split(
        train_texts,
        train_labels,
        test_size=0.20,
        random_state=SEED,
        stratify=train_labels,
    )
    validation_texts.extend(hard_validation)
    validation_labels.extend([0] * len(hard_validation))

    model = Pipeline([
        ("features", FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=40_000, sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=60_000, sublinear_tf=True)),
        ])),
        ("classifier", LogisticRegression(C=2.0, class_weight="balanced", max_iter=1_000, random_state=SEED)),
    ])

    with mlflow.start_run() as run:
        mlflow.log_params({
            "model_version": MODEL_VERSION,
            "seed": SEED,
            "word_ngram_range": "1,2",
            "char_ngram_range": "3,5",
            "min_df": 2,
            "max_features": 100_000,
            "C": 2.0,
            "class_weight": "balanced",
            "dataset_revision": DATASET_REVISION,
        })
        model.fit(fit_texts, fit_labels)
        validation_scores = model.predict_proba(validation_texts)[:, list(model.classes_).index(1)]
        threshold = select_threshold(np.asarray(validation_labels), validation_scores)

        test_scores = model.predict_proba(test_texts)[:, list(model.classes_).index(1)]
        test_metrics = calculate_metrics(np.asarray(test_labels), test_scores, threshold)
        hard_scores = model.predict_proba(hard_test)[:, list(model.classes_).index(1)]
        hard_fpr = float((hard_scores >= threshold).mean())
        metrics = {**test_metrics, "hard_benign_fpr": hard_fpr}
        release_passed = bool(float(metrics["recall"]) >= 0.90 and hard_fpr <= 0.05)

        scalar_metrics = {key: value for key, value in metrics.items() if isinstance(value, float)}
        mlflow.log_metrics(scalar_metrics)
        mlflow.log_metric("decision_threshold", threshold)
        mlflow.log_metric("release_passed", float(release_passed))
        mlflow.sklearn.log_model(
            model,
            "internal_pickle_model",
            input_example=np.asarray(fit_texts[:3], dtype=str),
        )

        model_path = output / "model.skops"
        dump(model, model_path)
        artifact_hash = sha256_file(model_path)
        unknown_types = get_untrusted_types(file=model_path)
        if unknown_types:
            raise RuntimeError(f"Exported artifact contains unapproved types: {unknown_types}")
        reloaded = load(model_path, trusted=[])
        if not np.allclose(model.predict_proba(test_texts), reloaded.predict_proba(test_texts)):
            raise RuntimeError("Reloaded artifact predictions differ from the trained pipeline")

        metadata = {
            "model_name": "prompt-injection-detector",
            "model_version": MODEL_VERSION,
            "model_type": "tfidf-logistic-regression",
            "artifact_sha256": artifact_hash,
            "labels": {"0": "benign", "1": "injection"},
            "injection_label": "1",
            "decision_threshold": threshold,
            "training_dataset_version": "deepset-main+hard-benign-v0.1.0",
            "evaluation_dataset_version": "0.1.0",
            "created_at": datetime.now(UTC).isoformat(),
            "mlflow_run_id": run.info.run_id,
            "release_passed": release_passed,
        }
        dataset_manifest = {
            "sources": [
                {"name": "deepset/prompt-injections", "revision": DATASET_REVISION, "usage": "train-test"},
                {"name": "custom-hard-benign", "version": "0.1.0", "usage": "train-validation-test"},
            ],
            "train_hash": sha256_rows(fit_texts, list(map(int, fit_labels))),
            "validation_hash": sha256_rows(validation_texts, list(map(int, validation_labels))),
            "test_hash": sha256_rows(test_texts, test_labels),
            "exact_train_test_overlap": 0,
            "seed": SEED,
        }
        (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        (output / "evaluation.json").write_text(json.dumps({"threshold": threshold, "metrics": metrics}, indent=2), encoding="utf-8")
        (output / "dataset_manifest.json").write_text(json.dumps(dataset_manifest, indent=2), encoding="utf-8")
        shutil.copyfile(Path(__file__).with_name("requirements-kaggle.txt"), output / "requirements.txt")
        shutil.copyfile(Path(__file__).resolve().parents[1] / "MODEL_CARD.md", output / "README.md")
        mlflow.log_artifacts(str(output), artifact_path="release")

    hf_commit = None
    repo_id = os.getenv("HF_MODEL_REPO")
    token = os.getenv("HF_TOKEN")
    if upload and release_passed and repo_id and token:
        api = HfApi(token=token)
        api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
        commit = api.upload_folder(
            folder_path=output,
            repo_id=repo_id,
            repo_type="model",
            commit_message=f"Release injection model v{MODEL_VERSION}",
        )
        hf_commit = commit.oid
        api.create_tag(repo_id=repo_id, tag=f"v{MODEL_VERSION}", revision=hf_commit, repo_type="model")

    return TrainingResult(str(output), release_passed, MODEL_VERSION, threshold, metrics, hf_commit)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="/kaggle/working/release")
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()
    result = run_training(args.output_dir, upload=not args.no_upload)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
