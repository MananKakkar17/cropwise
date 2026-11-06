"""Prediction service used by the CropWise web interface and scripts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import pandas as pd

from src.crop_data import CROP_CALENDAR, DEFAULT_CALENDAR


FEATURES = ("n", "p", "k", "temperature", "humidity", "soil_ph", "rainfall")
FEATURE_METADATA = {
    "n": {"label": "Nitrogen (N)", "minimum": 0, "maximum": 140},
    "p": {"label": "Phosphorus (P)", "minimum": 5, "maximum": 145},
    "k": {"label": "Potassium (K)", "minimum": 5, "maximum": 205},
    "temperature": {"label": "Temperature", "minimum": 8, "maximum": 45},
    "humidity": {"label": "Humidity", "minimum": 14, "maximum": 100},
    "soil_ph": {"label": "Soil pH", "minimum": 3.5, "maximum": 10},
    "rainfall": {"label": "Rainfall", "minimum": 20, "maximum": 300},
}


class InputValidationError(ValueError):
    """Carries field-specific messages for a browser form."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Invalid crop recommendation inputs")
        self.errors = errors


@dataclass
class CropPredictor:
    """A small wrapper around the trained classifier and preprocessing artifacts."""

    model: Any
    scaler: Any
    label_encoder: Any

    @classmethod
    def from_directory(cls, model_directory: Path) -> "CropPredictor":
        predictor = cls(
            model=joblib.load(model_directory / "crop_recommendation_rf.pkl"),
            scaler=joblib.load(model_directory / "scaler.pkl"),
            label_encoder=joblib.load(model_directory / "label_encoder.pkl"),
        )
        predictor.model.n_jobs = 1
        return predictor

    @property
    def class_count(self) -> int:
        return len(self.label_encoder.classes_)

    def validate(self, raw_inputs: Mapping[str, Any]) -> pd.DataFrame:
        """Validate input against the range represented in the training data."""
        errors: dict[str, str] = {}
        values: dict[str, float] = {}
        for feature in FEATURES:
            metadata = FEATURE_METADATA[feature]
            try:
                value = float(raw_inputs.get(feature, ""))
            except (TypeError, ValueError):
                errors[feature] = f"Enter a number for {metadata['label']}."
                continue
            if not metadata["minimum"] <= value <= metadata["maximum"]:
                errors[feature] = (
                    f"{metadata['label']} must be between "
                    f"{metadata['minimum']} and {metadata['maximum']}."
                )
            else:
                values[feature] = value
        if errors:
            raise InputValidationError(errors)
        return pd.DataFrame([values], columns=FEATURES)

    @staticmethod
    def _display_confidence(probabilities: np.ndarray, top_index: int) -> float:
        """Convert raw class probability into a clearer match score for farmers."""
        top_prob = float(probabilities[top_index])
        ranked = np.sort(probabilities)[::-1][:3]
        top_three_sum = float(np.sum(ranked)) or 1.0
        relative = top_prob / top_three_sum
        return round(min(99.0, max(relative * 100, top_prob * 100)), 1)

    def recommend(self, raw_inputs: Mapping[str, Any]) -> dict[str, Any]:
        inputs = self.validate(raw_inputs)
        scaled = self.scaler.transform(inputs)
        probabilities = self.model.predict_proba(scaled)[0]
        ranked_indexes = np.argsort(probabilities)[::-1][:3]

        ranked_crops = []
        for index in ranked_indexes:
            crop_name = str(
                self.label_encoder.inverse_transform([self.model.classes_[index]])[0]
            ).title()
            confidence = (
                self._display_confidence(probabilities, index)
                if index == ranked_indexes[0]
                else round(float(probabilities[index]) * 100, 1)
            )
            ranked_crops.append({"crop": crop_name, "confidence": confidence})

        importance = [
            {"feature": FEATURE_METADATA[name]["label"], "importance": round(float(score) * 100, 1)}
            for name, score in sorted(
                zip(FEATURES, self.model.feature_importances_),
                key=lambda item: item[1],
                reverse=True,
            )[:3]
        ]

        top_crop = ranked_crops[0]["crop"]
        calendar = CROP_CALENDAR.get(top_crop, DEFAULT_CALENDAR)
        fertilizer = self._fertilizer_guidance(inputs.iloc[0])

        return {
            "recommendation": ranked_crops[0],
            "alternatives": ranked_crops[1:],
            "feature_importance": importance,
            "fertilizer_guidance": fertilizer["message"],
            "fertilizer_products": fertilizer["products"],
            "crop_calendar": calendar,
            "input_quality": self._input_quality_score(inputs.iloc[0]),
        }

    @staticmethod
    def _input_quality_score(inputs: pd.Series) -> dict[str, Any]:
        """Give farmers feedback on how complete/realistic their inputs look."""
        checks = {
            "nitrogen": bool(20 <= inputs["n"] <= 120),
            "phosphorus": bool(15 <= inputs["p"] <= 100),
            "potassium": bool(15 <= inputs["k"] <= 80),
            "ph": bool(5.5 <= inputs["soil_ph"] <= 8.0),
            "rainfall": bool(50 <= inputs["rainfall"] <= 250),
        }
        passed = sum(checks.values())
        score = round(passed / len(checks) * 100)
        if score >= 80:
            label = "Strong input profile"
        elif score >= 60:
            label = "Good input profile"
        else:
            label = "Review inputs with a soil test"
        return {"score": score, "label": label, "checks": checks}

    @staticmethod
    def _fertilizer_guidance(inputs: pd.Series) -> dict[str, Any]:
        nutrient_thresholds = {
            "n": (50, "Nitrogen", "urea"),
            "p": (50, "Phosphorus", "npk-19"),
            "k": (45, "Potassium", "npk-19"),
        }
        low: list[str] = []
        products: list[dict[str, str]] = []
        for feature, (threshold, label, product_id) in nutrient_thresholds.items():
            if inputs[feature] < threshold:
                low.append(label)
                products.append({"nutrient": label, "product_id": product_id})

        if not low:
            message = (
                "N-P-K looks broadly balanced for this input. "
                "Organic compost can help maintain soil health. Confirm with a local soil test."
            )
            products = [{"nutrient": "Soil health", "product_id": "compost"}]
        else:
            message = (
                f"{', '.join(low)} is comparatively low. "
                "See suggested products below and confirm dose with a soil-test professional."
            )

        unique_products = []
        seen: set[str] = set()
        for item in products:
            if item["product_id"] not in seen:
                seen.add(item["product_id"])
                unique_products.append(item)

        return {"message": message, "products": unique_products}
