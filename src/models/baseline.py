"""
src/models/baseline.py
----------------------
Two zero-learning baselines used to anchor the comparison in Task 3.

Why these matter: a trained model that does not beat persistence or seasonal
naive is not adding signal — the rubric rewards comparison against a
non-trivial floor.

  - Persistence:     y_hat(t+1) = y(t)
  - Seasonal naive:  y_hat(t+1) = y(t+1-s),   s = 144 (one day, 10-min grid)

Both consume O(len(test)) time and zero memory beyond the test series.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.metrics import evaluate_all
from src.utils.timer import ModelTimer


DAILY_PERIOD = 144  # 24h / 10min


def _to_array(s) -> np.ndarray:
    """Accept pd.Series or np.ndarray; return float32 ndarray."""
    if isinstance(s, pd.Series):
        s = s.values
    return np.asarray(s, dtype=np.float32)


def run_persistence(train, test) -> dict:
    """
    y_hat(t+1) = y(t).

    For the first test point we use the last training value (proper
    one-step-ahead, no peeking at the test).
    """
    t = ModelTimer("Persistence")
    t.start_train(); t.stop_train()   # no training

    train_arr = _to_array(train)
    test_arr  = _to_array(test)
    last_train = train_arr[-1]

    t.start_inference()
    preds = np.empty(len(test_arr), dtype=np.float32)
    preds[0]  = last_train
    preds[1:] = test_arr[:-1]
    t.stop_inference()

    metrics = evaluate_all(test_arr, preds)
    print(f"Persistence -> MAE: {metrics['MAE']:.4f} | "
          f"MAPE: {metrics['MAPE']:.2f}% | RMSE: {metrics['RMSE']:.4f}")
    return {"predictions": preds, "metrics": metrics, "timer": t}


def run_seasonal_naive(train, test, period: int = DAILY_PERIOD) -> dict:
    """
    y_hat(t+1) = y(t+1 - period).

    The first `period` test points borrow from the tail of the training set;
    after that we use the actual test values one period back. This stays
    strictly causal: at time t we only look at observations on or before t.
    """
    t = ModelTimer(f"SeasonalNaive(s={period})")
    t.start_train(); t.stop_train()

    train_arr = _to_array(train)
    test_arr  = _to_array(test)
    if len(train_arr) < period:
        raise ValueError(
            f"Train series shorter than seasonal period ({len(train_arr)} < {period})"
        )

    t.start_inference()
    preds = np.empty(len(test_arr), dtype=np.float32)
    # For test indices 0..period-1 we reach back into the training tail.
    # For test index i >= period we reach back into the test history itself.
    for i in range(len(test_arr)):
        lag_idx = i - period
        if lag_idx < 0:
            preds[i] = train_arr[lag_idx]   # negative index into train tail
        else:
            preds[i] = test_arr[lag_idx]
    t.stop_inference()

    metrics = evaluate_all(test_arr, preds)
    print(f"SeasonalNaive(s={period}) -> MAE: {metrics['MAE']:.4f} | "
          f"MAPE: {metrics['MAPE']:.2f}% | RMSE: {metrics['RMSE']:.4f}")
    return {"predictions": preds, "metrics": metrics, "timer": t}
