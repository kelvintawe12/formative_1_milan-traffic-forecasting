"""
src/eda/stats.py
----------------
Statistical analysis functions for Task 2:
stationarity tests, decomposition, ACF/PACF.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.tsa.seasonal import seasonal_decompose


def adf_test(series: pd.Series, title: str = "") -> dict:
    """
    Augmented Dickey-Fuller stationarity test.

    H0: Series has a unit root (non-stationary)
    Reject H0 if p-value < 0.05 → series is stationary.
    """
    result = adfuller(series.dropna(), autolag="AIC")
    output = {
        "ADF Statistic": result[0],
        "p-value":       result[1],
        "Lags Used":     result[2],
        "Obs Used":      result[3],
        "Critical Values": result[4],
        "Stationary":    result[1] < 0.05,
    }
    print(f"\n── ADF Test: {title} ──")
    print(f"  ADF Statistic : {output['ADF Statistic']:.4f}")
    print(f"  p-value       : {output['p-value']:.4f}")
    for k, v in output["Critical Values"].items():
        print(f"  Critical ({k}) : {v:.4f}")
    print(f"  → {'STATIONARY' if output['Stationary'] else 'NON-STATIONARY'} at 5% level")
    return output


def rolling_statistics(
    series: pd.Series,
    window: int = 144,
    ax=None,
    title: str = "",
):
    """
    Plot rolling mean and standard deviation alongside the original series.
    window=144 corresponds to 1 day (144 × 10min).
    """
    roll_mean = series.rolling(window=window).mean()
    roll_std  = series.rolling(window=window).std()

    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 4))

    ax.plot(series, label="Original", alpha=0.5, linewidth=0.8)
    ax.plot(roll_mean, label=f"Rolling Mean (w={window})", color="orange")
    ax.plot(roll_std,  label=f"Rolling Std (w={window})", color="red")
    ax.set_title(f"Rolling Statistics — {title}")
    ax.set_xlabel("Time")
    ax.set_ylabel("Traffic")
    ax.legend()
    return ax


def decompose_series(
    series: pd.Series,
    period: int = 144,
    model: str = "additive",
):
    """
    Seasonal decomposition into trend, seasonal, and residual components.

    period=144 → daily seasonality (1 day = 144 × 10min intervals)
    model='additive' assumes: observed = trend + seasonal + residual
    """
    result = seasonal_decompose(series.dropna(), model=model, period=period)

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
    result.observed.plot(ax=axes[0], title="Observed")
    result.trend.plot(ax=axes[1], title="Trend")
    result.seasonal.plot(ax=axes[2], title="Seasonal")
    result.resid.plot(ax=axes[3], title="Residual")
    plt.tight_layout()
    return fig, result


def plot_acf_pacf(
    series: pd.Series,
    lags: int = 200,
    title: str = "",
):
    """
    Plot ACF and PACF to identify temporal dependencies.

    ACF  — reveals MA order q and seasonal patterns
    PACF — reveals AR order p
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6))

    acf_vals  = acf(series.dropna(), nlags=lags, fft=True)
    pacf_vals = pacf(series.dropna(), nlags=lags)

    ax1.stem(acf_vals, markerfmt=" ", basefmt="-")
    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.axhline(1.96 / np.sqrt(len(series)), color="red", linestyle="--", label="95% CI")
    ax1.axhline(-1.96 / np.sqrt(len(series)), color="red", linestyle="--")
    ax1.set_title(f"ACF — {title}")
    ax1.set_xlabel("Lag")
    ax1.legend()

    ax2.stem(pacf_vals, markerfmt=" ", basefmt="-")
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.axhline(1.96 / np.sqrt(len(series)), color="red", linestyle="--", label="95% CI")
    ax2.axhline(-1.96 / np.sqrt(len(series)), color="red", linestyle="--")
    ax2.set_title(f"PACF — {title}")
    ax2.set_xlabel("Lag")
    ax2.legend()

    plt.tight_layout()
    return fig
