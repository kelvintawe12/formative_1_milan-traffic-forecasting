"""
src/models/tuning.py
--------------------
Hyperparameter selection helpers for the three forecasting models.

Compute budget on a workstation:
  - SARIMA at s=144 is the bottleneck. We search a *small* (p,d,q)(P,D,Q,s)
    grid using AIC on the training fit (no walk-forward) — picking by AIC is
    standard for SARIMA order selection and avoids the cost of doing rolling
    forecasts inside the search.
  - LSTM / Transformer use a held-out tail of the training data as
    validation. A small random search beats a full grid for ~the same budget,
    so we expose both interfaces; the notebook uses a random search.

All searches are deterministic given the seed argument so the report can
quote reproducible "best" configurations.
"""

from __future__ import annotations

import itertools
import random
import time
import warnings
from typing import Iterable

import numpy as np
import pandas as pd

# Heavy imports are done lazily inside the functions that need them so this
# module is importable in environments where statsmodels / torch are missing.


# ─── SARIMA: AIC grid search ──────────────────────────────────────────────────
def sarima_aic_search(
    train: pd.Series,
    p_range: Iterable[int] = (0, 1, 2),
    d_range: Iterable[int] = (0, 1),
    q_range: Iterable[int] = (0, 1, 2),
    P_range: Iterable[int] = (0, 1),
    D_range: Iterable[int] = (0, 1),
    Q_range: Iterable[int] = (0, 1),
    s: int = 144,
    max_combos: int | None = 24,
    subsample: int | None = 144 * 7,
) -> pd.DataFrame:
    """
    Fit SARIMA on a *subsample* of the training tail for each grid point and
    rank by AIC. Returns a DataFrame sorted ascending by AIC.

    Subsampling is essential — a single SARIMA(1,1,1)(1,1,1,144) fit on the
    full 8-week training series can take minutes; we use the last 7 days for
    order selection and re-fit the chosen order on the full series in the
    main pipeline.

    `max_combos` caps total fits as a safety net. Pass None to disable.
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    series = train.iloc[-subsample:] if subsample else train

    combos = list(itertools.product(p_range, d_range, q_range,
                                    P_range, D_range, Q_range))
    if max_combos is not None and len(combos) > max_combos:
        # Deterministic prune: keep evenly-spaced combos rather than a tail.
        step = max(1, len(combos) // max_combos)
        combos = combos[::step][:max_combos]

    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for (p, d, q, P, D, Q) in combos:
            t0 = time.perf_counter()
            try:
                model = SARIMAX(
                    series,
                    order=(p, d, q),
                    seasonal_order=(P, D, Q, s),
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                fit = model.fit(disp=False, maxiter=50)
                rows.append({
                    "order":          (p, d, q),
                    "seasonal_order": (P, D, Q, s),
                    "aic":            fit.aic,
                    "bic":            fit.bic,
                    "fit_seconds":    round(time.perf_counter() - t0, 2),
                    "converged":      fit.mle_retvals.get("converged", None),
                })
            except Exception as e:                              # noqa: BLE001
                rows.append({
                    "order":          (p, d, q),
                    "seasonal_order": (P, D, Q, s),
                    "aic":            float("inf"),
                    "bic":            float("inf"),
                    "fit_seconds":    round(time.perf_counter() - t0, 2),
                    "converged":      False,
                    "error":          str(e),
                })

    return pd.DataFrame(rows).sort_values("aic").reset_index(drop=True)


# ─── Neural: random search on a validation tail ───────────────────────────────
def _split_train_val(X, y, val_frac: float = 0.1):
    n_val = max(1, int(len(X) * val_frac))
    return X[:-n_val], y[:-n_val], X[-n_val:], y[-n_val:]


def random_search_neural(
    train_fn,
    X_train: np.ndarray,
    y_train: np.ndarray,
    base_config: dict,
    search_space: dict,
    n_trials: int = 6,
    val_frac: float = 0.1,
    seed: int = 0,
) -> pd.DataFrame:
    """
    Random search over the keys in `search_space`. Each trial:
      1. samples one value per searched key,
      2. trains via `train_fn(X_tr, y_tr, config)` on the inner train,
      3. evaluates val MSE on the held-out tail.

    `train_fn` must follow the signature of `lstm_model.train_lstm` /
    `transformer_model.train_transformer` (returns {"model", "device", ...}).

    Returns a DataFrame sorted ascending by val_mse.
    """
    import torch

    rng = random.Random(seed)
    X_tr, y_tr, X_val, y_val = _split_train_val(X_train, y_train, val_frac)

    rows = []
    for trial in range(n_trials):
        cfg = dict(base_config)
        for k, choices in search_space.items():
            cfg[k] = rng.choice(list(choices))

        t0 = time.perf_counter()
        fitted = train_fn(X_tr, y_tr, cfg)
        model  = fitted["model"]
        device = fitted["device"]

        model.eval()
        with torch.no_grad():
            X_v = torch.tensor(X_val).unsqueeze(-1).to(device)
            y_v = torch.tensor(y_val).to(device)
            preds = model(X_v)
            val_mse = float(torch.mean((preds - y_v) ** 2).cpu())

        rows.append({
            "trial":      trial,
            "config":     {k: cfg[k] for k in search_space},
            "val_mse":    val_mse,
            "wall_s":     round(time.perf_counter() - t0, 1),
        })
        print(f"  trial {trial}: val_mse={val_mse:.6f}  cfg={rows[-1]['config']}")

    return pd.DataFrame(rows).sort_values("val_mse").reset_index(drop=True)


# ─── Default search spaces used by the notebook ───────────────────────────────
LSTM_SEARCH_SPACE = {
    "hidden_size": [64, 128, 256],
    "num_layers":  [1, 2],
    "dropout":     [0.1, 0.2, 0.3],
    "lr":          [1e-3, 5e-4, 2e-4],
}

TRANSFORMER_SEARCH_SPACE = {
    "d_model":         [32, 64, 128],
    "nhead":           [2, 4],
    "num_layers":      [1, 2, 3],
    "dim_feedforward": [128, 256, 512],
    "dropout":         [0.1, 0.2],
    "lr":              [1e-3, 5e-4, 2e-4],
}
