# Comparative Time-Series Analysis and Forecasting of Mobile Network Traffic

*IEEE-style report skeleton. Replace every `[FILL]` placeholder with content
from your notebook runs. Numbers should be quoted to the precision the
notebooks emit (4 decimals for MAE/RMSE, 2 for MAPE).*

---

## Abstract

Mobile network traffic from the Telecom Italia Milan grid (10 000 cells × 62
days, ~20 GB raw) is analysed and forecast one step ahead at 10-minute
resolution. We (i) build a memory-bounded streaming pipeline that aggregates
the raw 20 GB to a [FILL] GB partitioned Parquet store, (ii) characterise
the spatial, temporal, and statistical structure of the data, and (iii)
compare three forecasting algorithms — SARIMA, LSTM, and a Transformer —
against two zero-learning baselines on the test week 16–22 Dec 2013, for
three representative cells. [FILL: one-sentence headline result, e.g. "The
Transformer attains the lowest MAE on 2/3 areas while SARIMA remains
competitive in inference cost"].

**Keywords —** time-series forecasting, mobile network traffic, SARIMA,
LSTM, Transformer, large-scale data processing.

---

## I. Introduction

[FILL: 1 paragraph — problem statement (why one-step-ahead traffic
forecasts matter for radio resource management), positioning against
[Barlacchi et al., 2015], and a sentence on each of the three tasks.]

---

## II. Data Handling and Memory Management *(Task 1)*

### A. Dataset and constraints
The raw release is one tab-separated file per day, [FILL N] files totalling
[FILL] GB. Each row is `(square_id, time_interval, country_code, sms_in,
sms_out, call_in, call_out, internet_traffic)`. The paper's field order is
known to be incorrect; the loader follows the corrected order. Only
`(square_id, time_interval, internet_traffic)` is required, and
`internet_traffic` must be summed across `country_code` to recover one value
per (cell, 10-minute interval) — failing to do so silently inflates the
dataset by ~200× and makes the time-series ill-defined.

### B. Pipeline
The loader (`src/data/loader.py`) implements:

1. Per-file chunked read (`pd.read_csv(chunksize=1_000_000)`),
2. `usecols` pruning (8 → 3 columns),
3. Dtype downcast (`square_id` int64 → int16, `internet_traffic` float64 → float32),
4. Per-chunk `groupby(square_id, time_interval).sum()`,
5. Streaming write of one Snappy-Parquet shard per source file.

Steps 4 and 5 are the load-bearing optimisations: 4 collapses the
country-code duplication, and 5 means the full dataset is never
co-resident in memory.

Downstream code uses two selective readers:
`load_area_from_parquet(path, square_ids)` (pyarrow predicate pushdown)
and `total_traffic_per_area(path)` (one-pass `np.bincount` over row groups).

### C. Memory results
| Stage | Memory |
|---|---|
| Baseline single-file load (8 cols, default dtypes) | [FILL] MB |
| Optimised single-file load (3 cols, downcast, aggregated) | [FILL] MB |
| Reduction factor (single file) | [FILL]× |
| Full-dataset naïve extrapolation | [FILL] GB |
| Streaming pipeline peak RAM | ~[FILL] MB |
| Parquet-on-disk total | [FILL] GB |
| Raw → Parquet disk reduction | [FILL]× |

### D. Hardware and limitations
[FILL: CPU model, RAM, GPU model + CUDA version, OS. Reproduce values from
notebook 01 §1.1.] The 20 GB raw dataset on a 16 GB workstation makes any
"load it all" approach infeasible — the design above keeps peak RAM bounded
by chunk size irrespective of total dataset size. Resumability (idempotent
shard writes) was important during development since a full conversion
takes [FILL] minutes wall-clock.

---

## III. Exploratory Data Analysis *(Task 2)*

### A. Spatial heterogeneity — PDF of per-cell totals
[FIG `pdf_total_traffic.png`]. Skewness = [FILL], kurtosis = [FILL]. The
distribution is heavy right-tailed: central Milan cells dominate by orders
of magnitude while the periphery clusters near the mode.

### B. Temporal behaviour — three target cells
[FIG `time_series_three_areas.png`]. Cells: top-traffic = `[FILL square_id]`,
4159, 4556. All three exhibit a strong daily cycle (morning ramp ≈ 07:00,
evening peak ≈ 21:00, overnight trough). Magnitude differs by [FILL]×
between the top cell and the others; weekday/weekend modulation is
clearest on the top cell.

### C. Stationarity
[TBL: ADF results per cell.] All three p-values < 0.05 → reject unit-root.
However, rolling statistics show a non-constant level driven by the weekly
cycle, so seasonal differencing remains useful for SARIMA.

### D. Decomposition (top cell, 2 weeks, period = 144)
[FIG `decomposition_top_area.png`]. Trend ≈ flat over the window, seasonal
component is a clean ~24 h cycle, residuals concentrate around occasional
event-shaped spikes.

### E. ACF / PACF
[FIG `acf_pacf_*.png`]. Strong ACF lobe at lag 144 confirms the daily
period. PACF cuts off after [FILL] lags — informs the AR-order choice for
SARIMA. Secondary ACF lobe at lag 1008 (1 week) is visible but smaller.

### F. Spatial heatmap
[FIG `spatial_heatmap.png`]. Hot spots: Duomo / business district, [FILL
named hubs]. The 100×100 grid clearly separates the dense centre from
sparse periphery.

### G. Anomalies
Z > 3 outliers: [FILL N] points ([FILL]% of samples). Notable dates inside
the test week: [FILL — list any].

---

## IV. Forecasting Models *(Task 3)*

### A. Problem setup
At each test step *t* (10-minute resolution) each model receives a history
$x_{1:t}$ and outputs $\hat{y}_{t+1}$. We forecast Dec 16–22 (Mon–Sun) on
each of three cells. Train = everything before Dec 16. No information from
the test week is used in either training or hyper-parameter selection.

### B. Baselines (anchors)
- **Persistence** — $\hat{y}_{t+1}=y_t$.
- **Seasonal-naive (s=144)** — $\hat{y}_{t+1}=y_{t+1-144}$.

These set the floor below which a learned model cannot be considered useful.

### C. SARIMA
SARIMA(p,d,q)(P,D,Q,144). Order chosen by AIC grid (subsampled to last 7
days of training to keep search time bounded; see `src/models/tuning.py`).
Selected order: [FILL]. Inference uses walk-forward one-step-ahead with
`result.append(refit=False)`.

### D. LSTM
Stacked LSTM (2 layers) → dropout → linear head. Input: window of 144
scaled values (one full day). MinMax-scaled on train only.
Search space: hidden_size ∈ {64, 128, 256}, num_layers ∈ {1, 2}, dropout
∈ {0.1, 0.2, 0.3}, lr ∈ {1e-3, 5e-4, 2e-4}; 6 random trials on the
top-traffic cell with 10% validation tail. Selected: [FILL].

### E. Transformer
Linear input projection → sinusoidal positional encoding → N encoder
layers (multi-head self-attention + FFN) → mean-pool → linear head.
Same scaling and window as LSTM. Search space: d_model ∈ {32, 64, 128},
nhead ∈ {2, 4}, num_layers ∈ {1, 2, 3}, dim_feedforward ∈ {128, 256, 512},
dropout ∈ {0.1, 0.2}, lr ∈ {1e-3, 5e-4, 2e-4}; 6 random trials. Selected:
[FILL].

### F. Quantitative results
Per-cell tables (MAE / MAPE / RMSE) from `outputs/tables/metrics_*.csv`:

[FILL — paste the three CSVs as Markdown tables here.]

Timing (averaged over three cells), `outputs/tables/timing_table.csv`:

[FILL.]

### G. Forecast plots
9 plots (3 models × 3 cells, plus 2 baselines) under
`outputs/figures/forecast_*.png`. [FIG.]

### H. Comparative analysis
[FILL — directly tie back to Task 2 findings. Suggested structure:]

1. *Best on MAE.* [Model] wins on [N]/3 cells. The advantage is largest on
   [which cell] because [its dynamics show … from Task 2 §…].
2. *Best on training time.* Persistence/seasonal-naive trivially. Among
   trained models, [Model] is fastest because [reason]. SARIMA at s=144
   costs [FILL] s of MLE per cell.
3. *Best on inference cost.* [Model] — relevant if the forecast has to
   run in a control loop.
4. *Recommended pick.* [Model], on the grounds of [combination of
   accuracy + cost + alignment with the dominant daily seasonality
   identified in §III-E].

### I. Failure analysis
- *Hourly heatmap* (§4.7): [FILL] — which hours the trained models lose
  most relative to the baselines.
- *Day-of-week* (§4.8): [FILL] — typically Saturday/Sunday.
- *Error CDF* (§4.9): [FILL — compare 50th/95th percentile errors of best
  two models.]
- *Root cause.* The largest individual misses fall on [FILL — concrete
  dates], which coincide with anomalies flagged in Task 2 §2.8.
- *Mitigations.* Exogenous calendar/holiday features (SARIMAX), weekly
  lag inputs for the neural models, quantile-loss training to penalise
  tail errors.

---

## V. Reproducibility

```
cd milan-traffic-forecasting
conda env create -f environment.yml && conda activate milan-traffic
python run_pipeline.py        # runs notebooks 01 → 04 in order
```

Repository layout follows `README.md`. All randomness is seeded inside the
tuning helpers; SARIMA is deterministic; neural training uses
`torch.manual_seed(0)` (see notebook 03 cell-imports if you change this).

---

## VI. References

[1] G. Barlacchi *et al.*, "A multi-source dataset of urban life in the
city of Milan and the Province of Trentino," *Scientific Data*, 2015.

[2] V. Vaswani *et al.*, "Attention Is All You Need," *NeurIPS*, 2017.

[3] S. Hochreiter and J. Schmidhuber, "Long Short-Term Memory," *Neural
Computation*, 1997.

[4] G. E. P. Box, G. M. Jenkins, *Time Series Analysis: Forecasting and
Control*, 5th ed., Wiley, 2015.

[FILL — add any additional refs.]
