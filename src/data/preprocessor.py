"""
src/data/preprocessor.py
-------------------------
Preprocessing, normalization, and sequence generation for neural models.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple


# ── Test period (never used in training or validation) ─────────────────────────
TEST_START = "2013-12-16"
TEST_END   = "2013-12-22 23:59:59"


def train_test_split_by_date(
    series: pd.Series,
    test_start: str = TEST_START,
) -> Tuple[pd.Series, pd.Series]:
    """
    Split a time series into train and test sets by date.
    Test set = Dec 16–22 (strictly held out).
    """
    train = series[series.index < test_start]
    test  = series[series.index >= test_start]
    return train, test


def fit_scaler(train: pd.Series) -> Tuple[np.ndarray, MinMaxScaler]:
    """
    Fit a MinMaxScaler on training data only.
    Returns scaled train array and the fitted scaler.
    """
    scaler = MinMaxScaler(feature_range=(0, 1))
    train_scaled = scaler.fit_transform(train.values.reshape(-1, 1)).flatten()
    return train_scaled, scaler


def scale_series(series: pd.Series, scaler: MinMaxScaler) -> np.ndarray:
    """Apply a pre-fitted scaler to a series (for test data)."""
    return scaler.transform(series.values.reshape(-1, 1)).flatten()


def inverse_scale(values: np.ndarray, scaler: MinMaxScaler) -> np.ndarray:
    """Inverse transform scaled predictions back to original scale."""
    return scaler.inverse_transform(values.reshape(-1, 1)).flatten()


def create_sequences(
    data: np.ndarray,
    seq_length: int = 144,  # 144 × 10min = 1 day of history
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build (X, y) pairs for supervised sequence-to-one forecasting.

    Each X[i] is a window of `seq_length` past values.
    Each y[i] is the next value (one-step-ahead target).

    Args:
        data:       1D array of scaled traffic values
        seq_length: Number of past timesteps used as input

    Returns:
        X: shape (n_samples, seq_length)
        y: shape (n_samples,)
    """
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i : i + seq_length])
        y.append(data[i + seq_length])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def fill_missing(series: pd.Series, method: str = "linear") -> pd.Series:
    """
    Fill missing timesteps via interpolation.
    'linear' is appropriate for smooth traffic signals.
    """
    full_index = pd.date_range(series.index.min(), series.index.max(), freq="10min")
    series = series.reindex(full_index)
    series = series.interpolate(method=method)
    return series
