"""Compare candidate classifiers and train the final CropWise model.

The experiment deliberately holds out 20 percent of the data before any model
selection. Cross-validation chooses the model on the remaining training set;
the test split is used only once for the final, unbiased accuracy estimate.

Run: python -m src.train_model
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.tree import DecisionTreeClassifier

from src.preprocess import load_crop_dataset, split_features_and_target


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "crop_recommendation_cleaned.csv"
MODEL_DIRECTORY = PROJECT_ROOT / "models"
REPORT_DIRECTORY = PROJECT_ROOT / "reports"
RANDOM_STATE = 42


def candidate_models() -> dict[str, object]:
    """Return models with intentionally fixed parameters for reproducibility."""
    return {
        "Decision Tree": DecisionTreeClassifier(random_state=RANDOM_STATE, max_depth=None),
        "K Nearest Neighbors": KNeighborsClassifier(n_neighbors=5, weights="distance"),
        "Random Forest": RandomForestClassifier(
            n_estimators=400,
            random_state=RANDOM_STATE,
            n_jobs=1,
            class_weight="balanced",
        ),
        "Extra Trees": ExtraTreesClassifier(
            n_estimators=400,
            random_state=RANDOM_STATE,
            n_jobs=1,
            class_weight="balanced",
        ),
    }


def build_pipeline(model: object) -> Pipeline:
    """Scale inside the pipeline to prevent data leakage during cross-validation."""
    return Pipeline([("scaler", MinMaxScaler()), ("classifier", model)])


def compare_models(train_x, train_y, test_x, test_y) -> tuple[str, Pipeline, list[dict[str, float | str]]]:
    """Evaluate candidate models on the identical split and return the winner."""
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    results: list[dict[str, float | str]] = []
    best_name = ""
    best_pipeline: Pipeline | None = None
    best_cv_score = -1.0

    for name, model in candidate_models().items():
        pipeline = build_pipeline(model)
        cv_scores = cross_val_score(pipeline, train_x, train_y, cv=folds, scoring="accuracy", n_jobs=1)
        pipeline.fit(train_x, train_y)
        test_score = accuracy_score(test_y, pipeline.predict(test_x))
        result = {
            "model": name,
            "cross_validation_mean": round(float(cv_scores.mean()), 4),
            "cross_validation_std": round(float(cv_scores.std()), 4),
            "test_accuracy": round(float(test_score), 4),
        }
        results.append(result)
        if cv_scores.mean() > best_cv_score:
            best_name, best_pipeline, best_cv_score = name, pipeline, float(cv_scores.mean())

    if best_pipeline is None:
        raise RuntimeError("No candidate model completed training.")
    return best_name, best_pipeline, results


def save_artifacts(pipeline: Pipeline, encoder: LabelEncoder) -> None:
    """Save precisely the model, scaler, and labels expected by the web app."""
    MODEL_DIRECTORY.mkdir(exist_ok=True)
    joblib.dump(pipeline.named_steps["classifier"], MODEL_DIRECTORY / "crop_recommendation_rf.pkl")
    joblib.dump(pipeline.named_steps["scaler"], MODEL_DIRECTORY / "scaler.pkl")
    joblib.dump(encoder, MODEL_DIRECTORY / "label_encoder.pkl")


def train() -> None:
    dataset = load_crop_dataset(DATASET_PATH)
    features, labels = split_features_and_target(dataset)
    encoder = LabelEncoder()
    encoded_labels = encoder.fit_transform(labels)

    train_x, test_x, train_y, test_y = train_test_split(
        features,
        encoded_labels,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=encoded_labels,
    )

    winner, winning_pipeline, comparison = compare_models(train_x, train_y, test_x, test_y)
    final_predictions = winning_pipeline.predict(test_x)
    test_accuracy = accuracy_score(test_y, final_predictions)
    save_artifacts(winning_pipeline, encoder)

    REPORT_DIRECTORY.mkdir(exist_ok=True)
    experiment = {
        "dataset_rows": len(dataset),
        "features": list(features.columns),
        "split": {"train_rows": len(train_x), "test_rows": len(test_x), "test_size": 0.20, "stratified": True},
        "selection_method": "5-fold stratified cross-validation on training split",
        "selected_model": winner,
        "selected_model_test_accuracy": round(float(test_accuracy), 4),
        "comparison": comparison,
    }
    (REPORT_DIRECTORY / "model_comparison.json").write_text(json.dumps(experiment, indent=2), encoding="utf-8")

    print(json.dumps(experiment, indent=2))
    print("\nClassification report for the selected model:\n")
    print(classification_report(test_y, final_predictions, target_names=encoder.classes_))
    print(f"\nSaved model artifacts to {MODEL_DIRECTORY}")
    print(f"Saved comparison results to {REPORT_DIRECTORY / 'model_comparison.json'}")


if __name__ == "__main__":
    train()
