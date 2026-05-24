"""
SARIMA (Seasonal ARIMA) model for one-step-ahead traffic forecasting.

SARIMA(p,d,q)(P,D,Q,s) where:
  p,d,q = non-seasonal AR order, differencing, MA order
  P,D,Q = seasonal AR order, differencing, MA order
  s     = seasonal period (144 for daily seasonality at 10-min resolution)
"""

import numpy as np
import pandas as pd
import warnings
from statsmodels.tsa.statespace.sarimax import SARIMAX
from src.utils.metrics import evaluate_all
from src.utils.timer import ModelTimer

warnings.filterwarnings("ignore")


# ── Default SARIMA orders — tune via AIC/BIC in the notebook ──────────────────
# s=144: 144 intervals × 10min = 1 day (daily seasonality)
# s=1008: 1008 intervals × 10min = 1 week (weekly seasonality — expensive)
# We start with daily seasonality as a practical trade-off.
DEFAULT_ORDER         = (1, 1, 1)
DEFAULT_SEASONAL_ORDER = (1, 1, 1, 144)


def fit_sarima(
    train: pd.Series,
    order: tuple = DEFAULT_ORDER,
    seasonal_order: tuple = DEFAULT_SEASONAL_ORDER,
    model_name: str = "SARIMA",
) -> dict:
    """
    Fit a SARIMA model on the training series.

    Args:
        train:          Training time series (datetime-indexed)
        order:          (p, d, q)
        seasonal_order: (P, D, Q, s)
        model_name:     Label for timing report

    Returns:
        Dictionary with fitted model result and timer report
    """
    t = ModelTimer(model_name)
    t.start_train()

    model = SARIMAX(
        train,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    result = model.fit(disp=False)

    t.stop_train()
    print(f"SARIMA training complete. AIC: {result.aic:.2f}")
    print(result.summary())

    return {"result": result, "timer": t}


def predict_sarima(
    fitted: dict,
    test: pd.Series,
) -> np.ndarray:
    """
    Produce one-step-ahead rolling forecasts over the test period.

    For each step in the test set, we extend the in-sample fit by one step.
    This is the proper walk-forward evaluation approach.

    Args:
        fitted: Output of fit_sarima()
        test:   Test time series (Dec 16–22)

    Returns:
        Array of predictions aligned with test.index
    """
    result = fitted["result"]
    t = fitted["timer"]
    t.start_inference()

    preds = []
    for i in range(len(test)):
        forecast = result.forecast(steps=1)
        preds.append(float(forecast.iloc[0]))
        # Append the true observation to keep the model updated
        result = result.append(test.iloc[[i]], refit=False)

    t.stop_inference()
    return np.array(preds)


def run_sarima(
    train: pd.Series,
    test: pd.Series,
    order: tuple = DEFAULT_ORDER,
    seasonal_order: tuple = DEFAULT_SEASONAL_ORDER,
) -> dict:
    """
    Full SARIMA pipeline: fit → predict → evaluate.

    Returns:
        {
          "predictions": np.ndarray,
          "metrics": {"MAE": ..., "MAPE": ..., "RMSE": ...},
          "timer": ModelTimer
        }
    """
    fitted = fit_sarima(train, order, seasonal_order)
    predictions = predict_sarima(fitted, test)
    metrics = evaluate_all(test.values, predictions)

    print(f"\nSARIMA Metrics → MAE: {metrics['MAE']:.4f} | "
          f"MAPE: {metrics['MAPE']:.2f}% | RMSE: {metrics['RMSE']:.4f}")

    return {
        "predictions": predictions,
        "metrics": metrics,
        "timer": fitted["timer"],
    }
