"""Dataset loading and validation used before model training."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.predict import FEATURES


TARGET_COLUMN = "label"


def load_crop_dataset(path: Path) -> pd.DataFrame:
    """Load the cleaned crop dataset and fail early if its schema is incorrect."""
    dataset = pd.read_csv(path)
    expected = set(FEATURES) | {TARGET_COLUMN}
    missing_columns = expected - set(dataset.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Dataset is missing required columns: {missing}")
    dataset = dataset.loc[:, [*FEATURES, TARGET_COLUMN]].dropna().copy()
    if dataset.empty:
        raise ValueError("Dataset has no usable training rows after cleaning.")
    return dataset


def split_features_and_target(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Return model inputs and the human-readable crop target."""
    return dataset.loc[:, FEATURES], dataset[TARGET_COLUMN]
