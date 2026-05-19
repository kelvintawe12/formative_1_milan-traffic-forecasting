"""
src/eda/plots.py
----------------
Visualization functions for Task 2 EDA requirements.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def plot_traffic_pdf(
    total_traffic_per_area: pd.Series,
    save_path: str = None,
):
    """
    Plot the probability density function of total 2-month traffic
    across all 10,000 geographical areas.

    Args:
        total_traffic_per_area: Series indexed by square_id, values = total traffic
        save_path: If provided, save figure to this path
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.kdeplot(total_traffic_per_area, ax=ax, fill=True, color="steelblue", alpha=0.6)
    ax.set_title("PDF of Total 2-Month Internet Traffic Across 10,000 Areas")
    ax.set_xlabel("Total Internet Traffic")
    ax.set_ylabel("Density")
    ax.axvline(total_traffic_per_area.median(), color="red",
               linestyle="--", label=f"Median: {total_traffic_per_area.median():.2f}")
    ax.axvline(total_traffic_per_area.mean(), color="orange",
               linestyle="--", label=f"Mean: {total_traffic_per_area.mean():.2f}")
    ax.legend()
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_time_series_three_areas(
    series_dict: dict,
    two_weeks_only: bool = True,
    save_path: str = None,
):
    """
    Plot time series for three areas side by side or stacked.

    Args:
        series_dict: {"Area A (highest)": pd.Series, "Area 4159": ..., "Area 4556": ...}
        two_weeks_only: Slice to first two weeks
    """
    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=False)

    for ax, (label, series) in zip(axes, series_dict.items()):
        if two_weeks_only:
            start = series.index.min()
            end   = start + pd.Timedelta(weeks=2)
            series = series[series.index <= end]

        ax.plot(series, linewidth=0.8, color="steelblue")
        ax.set_title(f"Traffic Time Series — {label}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Internet Traffic")
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_traffic_heatmap(
    df_or_totals,
    save_path: str = None,
):
    """
    Spatial heatmap of total traffic intensity across the 100×100 grid.

    Args:
        df_or_totals: either
          - a DataFrame with columns [square_id, internet_traffic]
            (totals will be computed via groupby), or
          - a precomputed pd.Series indexed by square_id (preferred — produced
            by `loader.total_traffic_per_area`, no full-dataset load required).
    """
    if isinstance(df_or_totals, pd.Series):
        total = df_or_totals.reset_index()
        total.columns = ["square_id", "internet_traffic"]
    else:
        total = (df_or_totals.groupby("square_id")["internet_traffic"]
                             .sum().reset_index())

    # Map square_id (1–10000) to (row, col) in a 100×100 grid
    total["row"] = (total["square_id"].astype(int) - 1) // 100
    total["col"] = (total["square_id"].astype(int) - 1) % 100

    grid = total.pivot(index="row", columns="col", values="internet_traffic")

    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(grid, cmap="YlOrRd", aspect="auto", origin="lower")
    plt.colorbar(im, ax=ax, label="Total Internet Traffic")
    ax.set_title("Spatial Heatmap of Total 2-Month Internet Traffic (100×100 Grid)")
    ax.set_xlabel("Column (Grid X)")
    ax.set_ylabel("Row (Grid Y)")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_forecast_vs_actual(
    actual: pd.Series,
    predictions_dict: dict,
    area_label: str,
    save_path: str = None,
):
    """
    Overlay plot of actual vs. predicted traffic for one area.

    Args:
        actual:           True test series (datetime-indexed)
        predictions_dict: {"SARIMA": np.ndarray, "LSTM": ..., "Transformer": ...}
        area_label:       Title label for the area
    """
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(actual.index, actual.values, label="Actual", color="black",
            linewidth=1.2, zorder=5)

    colors = ["steelblue", "tomato", "seagreen"]
    for (model_name, preds), color in zip(predictions_dict.items(), colors):
        ax.plot(actual.index, preds, label=model_name, color=color,
                linewidth=1.0, linestyle="--", alpha=0.85)

    ax.set_title(f"Forecast vs. Actual — {area_label} (Dec 16–22)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Internet Traffic")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_training_curves(losses_dict: dict, save_path: str = None):
    """
    Plot training loss curves for LSTM and Transformer.

    Args:
        losses_dict: {"LSTM": [loss_per_epoch], "Transformer": [loss_per_epoch]}
    """
    fig, axes = plt.subplots(1, len(losses_dict), figsize=(14, 4))
    if len(losses_dict) == 1:
        axes = [axes]

    for ax, (model_name, losses) in zip(axes, losses_dict.items()):
        ax.plot(losses, label="Train Loss", color="steelblue")
        ax.set_title(f"{model_name} Training Loss")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("MSE Loss")
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig
