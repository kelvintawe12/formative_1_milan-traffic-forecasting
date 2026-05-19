"""
src/utils/metrics.py
--------------------
Evaluation metrics: MAE, MAPE, RMSE — with formulas documented.
"""

import numpy as np


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Mean Absolute Error
    MAE = (1/n) * Σ |y_true - y_pred|
    Measures average magnitude of errors. Same unit as the target.
    """
    return float(np.mean(np.abs(y_true - y_pred)))


def mape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-8) -> float:
    """
    Mean Absolute Percentage Error
    MAPE = (100/n) * Σ |y_true - y_pred| / (|y_true| + eps)
    Expresses error as a percentage. Sensitive to near-zero actuals.
    eps avoids division by zero.
    """
    return float(np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + eps))) * 100)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Root Mean Squared Error
    RMSE = sqrt((1/n) * Σ (y_true - y_pred)^2)
    Penalizes large errors more than MAE. Same unit as the target.
    """
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def evaluate_all(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Return all three metrics as a dictionary."""
    return {
        "MAE": mae(y_true, y_pred),
        "MAPE": mape(y_true, y_pred),
        "RMSE": rmse(y_true, y_pred),
    }
