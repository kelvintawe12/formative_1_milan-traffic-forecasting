# Comparative Time-Series Analysis and Forecasting of Mobile Network Traffic

## Abstract

This report analyses 62 days of 10-minute mobile-network activity from
the Telecom Italia Milan grid (10 000 cells, 19.4 GB raw) and forecasts
each series one step ahead. The work has three parts. First, I built a
streaming ETL that collapses the 19.4 GB raw release to a 0.40 GB
partitioned Parquet store (48.6× smaller on disk) without ever holding
the full dataset in memory. Second, I characterised the spatial,
temporal, and statistical structure of the data for three representative
cells. Third, I compared SARIMA, LSTM, and a Transformer encoder
against two zero-learning baselines (persistence and seasonal-naive)
on a held-out test week, December 16–22, 2013.

SARIMA(2,1,2) gives the lowest MAE on all three cells, improving on
persistence by 4–8 % while training in 1.3 s. The LSTM is roughly tied
with persistence. The Transformer underperforms both baselines because
its readout averages the encoder output across the full 24-hour input
window, which destroys the lag-1 signal that the data is dominated by.
At 10-minute resolution the value at t+1 is ≈95 % correlated with the
value at t, so models that surface lag-1 directly win; models whose
readout dilutes it lose.

**Keywords:** time-series forecasting, mobile network traffic, SARIMA,
LSTM, Transformer, large-scale data processing.

---

## I. Introduction

One-step-ahead traffic forecasts at the cell level support short-horizon
radio resource management: admission control, dynamic bandwidth
allocation, and proactive load-balancing [1]. I evaluated three model
families on the Telecom Italia Big Data Challenge release for Milan:
a classical statistical model (SARIMA), a recurrent neural network
(LSTM), and a Transformer encoder. Persistence and seasonal-naive
baselines anchor the comparison.

This report covers three things: a reproducible streaming pipeline for
the 19.4 GB raw release, a quantitative description of the spatial and
temporal heterogeneity of Milan's mobile traffic, and a controlled
comparison of the three models on three cells with training cost,
inference cost, and failure modes reported alongside accuracy.

---

## II. Data Handling and Memory Management *(Task 1)*

### A. Dataset and constraints
The raw release is one tab-separated file per day: 62 files, 19.38 GB
total. Each row has eight fields: `square_id`, `time_interval`,
`country_code`, `sms_in`, `sms_out`, `call_in`, `call_out`,
`internet_traffic`. I only need `square_id`, `time_interval`, and
`internet_traffic`, and the `internet_traffic` values have to be summed
across `country_code` to get one value per (cell, 10-minute interval).
Skipping this aggregation inflates the dataset by about 3.4× and leaves
the time series semantically meaningless. Note that the field order in
the original paper [1] is wrong; the loader uses the corrected order.

### B. Pipeline
For each raw file, `src/data/loader.py` does five things:

1. Chunked read with `pd.read_csv(chunksize=1_000_000)`.
2. `usecols=[square_id, time_interval, internet_traffic]` drops five
   columns at read time.
3. Dtype downcast: `square_id` int64 → int16, `internet_traffic`
   float64 → float32.
4. Per-chunk `groupby(square_id, time_interval).sum()` to collapse the
   country-code duplication.
5. Streaming write of one Snappy-Parquet shard per source file.

Downstream notebooks read this store through two selective helpers:
`load_area_from_parquet(path, square_ids)` uses pyarrow predicate
pushdown to pull only the rows for the cells of interest, and
`total_traffic_per_area(path)` uses a one-pass `np.bincount` over row
groups to get per-cell totals. The full aggregated dataset never sits
in memory all at once.

### C. Memory results
| Stage | Value |
|---|---:|
| Baseline single-file load (8 cols, default dtypes) | 295.6 MB / 4 842 625 rows |
| Optimised single-file load (3 cols, downcast, aggregated) | 19.23 MB / 1 439 982 rows |
| Per-file reduction | **15.4×** |
| Full-dataset naïve extrapolation | 17.9 GB in RAM (infeasible) |
| Streaming pipeline peak RAM | ≈ chunk size × few columns, a few hundred MB |
| Final Parquet store on disk | 0.40 GB |
| Raw → Parquet on-disk reduction | **48.6×** |
| Total streaming-aggregate wall time | 210.5 s (3 m 31 s) |
| Raw rows processed | 319 896 289 |
| Aggregated rows | 89 245 318 |

The 48.6× disk reduction comes from three sources stacking: Snappy
compression, the dtype downcast, and the country-code groupby (which on
its own accounts for the 3.4× factor).

### D. Hardware and challenges
- **Platform:** Windows 11 (10.0.22631), Intel Core i7 (Family 6, Model 186), Python 3.11.9, pandas 3.0.3, pyarrow 24.0.0, PyTorch 2.12.0 (CPU build, no CUDA).
- **Long path issue.** Windows 10/11 has a 260-character path limit by default. The first venv build failed because the project was unzipped at four nested levels. Moving the repo to `C:\milan\...` saved about 80 characters and fixed it.
- **Guestbook gate.** Harvard Dataverse blocks anonymous downloads of this dataset (guestbookID 96). I worked around it with an authenticated API token in the `DATAVERSE_API_TOKEN` environment variable. The downloader prints a clear remediation message when the token is missing.
- **Resumability.** Each shard is written atomically, so restarting the pipeline after a crash picks up where it left off. This mattered because the full SARIMA inference run takes roughly four hours.

---

## III. Exploratory Data Analysis *(Task 2)*

### A. Spatial heterogeneity: PDF of per-cell totals
See `pdf_total_traffic.png`. The distribution of two-month per-cell
totals is heavily right-skewed: skewness 4.27, kurtosis 25.52, median
2.78 × 10⁵, max 1.27 × 10⁷ (45× the median). Central business cells
dominate the periphery by orders of magnitude. The IQR (1.18 × 10⁵ to
5.78 × 10⁵) spans a 5× range, but the upper tail stretches another 20×
beyond the upper quartile.

### B. Temporal behaviour: three target cells
See `time_series_three_areas.png`. I picked three cells:

- **5161** — the top-traffic cell across the two months (1.27 × 10⁷ total). The afternoon spike on 2013-12-01 (Sunday 15:00–17:00) is consistent with a stadium event at nearby San Siro.
- **4159** — a moderate-traffic residential cell.
- **4556** — another moderate-traffic cell, with a slightly higher baseline than 4159.

All three follow the same daily envelope: a morning ramp around 07:00,
an evening plateau, and an overnight trough. The absolute magnitudes
differ by 6–10× between cells. The weekday/weekend modulation shows
most clearly on the top cell.

### C. Stationarity
| Cell | ADF statistic | p-value | Verdict (α = 0.05) |
|---|---:|---:|---|
| 5161 | −19.03 | 0.0000 | **Stationary** |
| 4159 | −12.86 | 0.0000 | **Stationary** |
| 4556 | −14.20 | 0.0000 | **Stationary** |

All three series reject the unit-root null at very high confidence. The
rolling-mean plots in `rolling_stats_*.png` show a non-constant *level*
driven by the weekly cycle, but the series themselves are still
covariance-stationary, which is why ARIMA-class models work directly on
the raw values rather than on differences.

### D. Decomposition
See `decomposition_top_area.png` (cell 5161, two weeks, period = 144,
additive). The trend is approximately flat. The seasonal component is
a clean 24-hour cycle with amplitude around 30–40 % of the daily peak.
The residuals are concentrated around occasional spikes, most clearly
the 2013-12-01 afternoon spike, rather than spread uniformly. This
points to event-driven anomalies rather than Gaussian noise.

### E. ACF / PACF
See `acf_pacf_*.png`. Two findings shape the model design:

1. The lag-1 autocorrelation is very high (around 0.95 on all cells), so successive 10-minute observations are nearly identical.
2. A clear secondary ACF lobe appears at lag 144 (24 hours), confirming the daily cycle. Its amplitude is roughly half the low-lag autocorrelation.

This combination predicts the eventual result: a model that surfaces
lag-1 directly (SARIMA AR(2)-I(1)-MA(2)) beats one that leans on the
daily cycle as its primary signal (seasonal-naive).

### F. Spatial heatmap
See `spatial_heatmap.png`. Activity concentrates in a dense central
cluster (the Duomo / business district). The top decile of cells forms
a clear core surrounded by a much lower-activity periphery.

### G. Anomalies
On cell 5161 there are 51 outliers at |z| > 3, or 0.57 % of samples.
The largest cluster on 2013-12-01 between 15:00 and 17:00, peaking at
8 044 versus a typical Sunday-afternoon level around 800 — a 10× spike.
The timing matches a Serie A match at San Siro that weekend and is the
single clearest event in the two-month window. None of the |z| > 3
outliers fall inside the test week (Dec 16–22), so the model comparison
runs on relatively well-behaved data.

---

## IV. Forecasting Models *(Task 3)*

### A. Problem setup
At each test step *t* (10-minute resolution) the model receives the
history $x_{1:t}$ and outputs $\hat{y}_{t+1}$. The test window is
December 16–22, 2013 (Monday to Sunday, 1 008 ten-minute intervals × 3
cells = 3 024 forecasts per model). The training data is everything
before December 16 (6 486 samples per cell). No information from the
test week is used in training or in hyperparameter selection.

### B. Baselines (anchors)
- **Persistence:** $\hat{y}_{t+1} = y_t$. Captures the lag-1 dynamics.
- **Seasonal-naive (s = 144):** $\hat{y}_{t+1} = y_{t+1-144}$. Captures the daily cycle.

### C. SARIMA
SARIMA(p,d,q)(P,D,Q,144). Order selected by AIC over a grid of 18
configurations, fit on the last 7 days of the training set
(`src/models/tuning.sarima_aic_search`). Top three by AIC:

| Order | Seasonal order | AIC |
|---|---|---:|
| **(2,1,2)** | **(0,0,0,144)** | **13 050.07** |
| (1,1,2) | (0,0,0,144) | 13 051.40 |
| (2,0,2) | (0,0,0,144) | 13 059.54 |

The AIC search rejected every seasonal term: the non-seasonal
AR(2)-I(1)-MA(2) configuration beat every candidate that included a
seasonal component. This is the first sign that the lag-1 dynamics
dominate the daily cycle at this resolution, which I return to in
§IV.H.

The SARIMAX summary for cell 5161 (AIC 88 671.79) shows all four
coefficients significant at p < 0.001, with AR.L1 ≈ 1.10 and
MA.L1 ≈ −1.50. With the first-order difference, this is effectively
smoothing the lag-1 signal with a small ARMA correction.

Inference is a proper walk-forward one-step-ahead loop:
`result.append(refit=False)` for 1 008 steps per cell.

### D. LSTM
Stacked LSTM → dropout → linear head. The input is a 144-step window of
MinMax-scaled lag values, i.e. one full day of history. I ran a random
search over six configurations on the top-traffic cell using a 10 %
validation tail. The selected configuration was hidden_size = 256,
num_layers = 2, dropout = 0.2, lr = 5 × 10⁻⁴, with a validation MSE of
6.58 × 10⁻⁴. The final model was trained for 30 epochs on CPU.

### E. Transformer
Linear input projection → sinusoidal positional encoding → N encoder
layers (multi-head self-attention + FFN) → **mean-pool across the
sequence** → linear head. Same scaling and window as the LSTM. Random
search over six configurations. The mean-pool readout is the mechanism
behind the model's poor accuracy on this dataset — see §IV.H for the
detailed analysis.

### F. Quantitative results

**Cell 5161 (top-traffic).** From `outputs/tables/metrics_Area_5161_TopTraffic.csv`:

| Model | MAE | MAPE (%) | RMSE |
|---|---:|---:|---:|
| Persistence | 78.87 | 11.06 | 119.73 |
| SeasonalNaive | 398.75 | 57.28 | 690.14 |
| **SARIMA** | **74.91** | **10.39** | **115.44** |
| LSTM | 104.26 | 18.99 | 151.96 |
| Transformer | 268.15 | 92.80 | 328.18 |

**Cell 4159.** From `outputs/tables/metrics_Area_4159.csv`:

| Model | MAE | MAPE (%) | RMSE |
|---|---:|---:|---:|
| Persistence | 12.53 | 8.51 | 17.20 |
| SeasonalNaive | 39.24 | 25.39 | 63.10 |
| **SARIMA** | **11.46** | **7.63** | **16.08** |
| LSTM | 12.92 | 9.21 | 17.48 |
| Transformer | 60.79 | 50.90 | 64.63 |

**Cell 4556.** From `outputs/tables/metrics_Area_4556.csv`:

| Model | MAE | MAPE (%) | RMSE |
|---|---:|---:|---:|
| Persistence | 25.50 | 7.99 | 35.32 |
| SeasonalNaive | 63.59 | 20.15 | 87.68 |
| **SARIMA** | **23.51** | **7.28** | **32.62** |
| LSTM | 24.34 | 7.72 | 33.22 |
| Transformer | 28.12 | 10.15 | 36.47 |

**Timing (averaged across the three cells).** From
`outputs/tables/timing_table.csv`:

| Model | Avg train time (s) | Avg inference time (s) |
|---|---:|---:|
| Persistence | 0.0 | 0.0 |
| SeasonalNaive | 0.0 | 0.0003 |
| **SARIMA** | **1.3** | 91.60 |
| LSTM | 2 253.03 | 7.90 |
| Transformer | 1 774.40 | 8.00 |

*Caveat on the inference column.* The neural models are evaluated by a
single batched forward pass over the 1 008 pre-built test windows, while
SARIMA does a true walk-forward with `result.append(refit=False)` for
every step. The ≈10× gap therefore measures *how much more expensive
walk-forward refit is*, not how the two would compare in a deployment
where both produce one prediction per arriving sample. With per-step
inference on both sides, the gap would shrink considerably.

### G. Comparative analysis

The accuracy ranking is the same on every cell and every metric:
SARIMA < Persistence ≈ LSTM ≪ SeasonalNaive < Transformer (lower is
better). There is no "depends on the area" caveat. SARIMA's edge over
persistence is 4–8 % on MAE. Persistence's edge over the LSTM is
0–25 % on MAE, depending on the cell.

On compute cost, SARIMA's 1.3 s of training time is dwarfed by the
30–40 minutes each neural model needed. The Transformer trained
slightly faster than the LSTM (mean-pool plus two encoder layers
versus two LSTM layers at hidden size 256) but its predictions are
essentially unusable. SARIMA's operational drawback is the per-step
refit during walk-forward inference: 92 s for a 1 008-step horizon is
fine offline but would need a state-space formulation for real-time
use.

Best model: SARIMA(2,1,2)(0,0,0,144). Four reasons:

- Lowest MAE, MAPE, and RMSE on every cell — 10 out of 10 metric–cell pairs.
- Training cost is two orders of magnitude lower than either neural model.
- The fitted coefficients are interpretable. AR.L1 ≈ 1.10 and MA.L1 ≈ −1.50, together with the unit difference, implement a smoothing of the lag-1 signal. That matches what the high lag-1 ACF predicted.
- The AIC search selected zero seasonal terms, which confirms that explicit daily seasonality is not needed once the lag-1 dynamics are modelled.

### H. Failure analysis

**Why seasonal-naive collapses.** Seasonal-naive is 5–10× worse than
persistence on MAE because lag-1 is much stronger than lag-144 in this
signal. The lag-144 ACF lobe is real and the daily decomposition is
clean, but on a 10-minute grid the value at *t+1* is around 95 %
correlated with *t* and only around 60 % correlated with *t − 24 h*.
A model that ignores lag-1 cannot compete here, no matter how well it
captures the cycle. This is the central diagnostic finding of the
study.

**Why the Transformer fails.** The failure is architectural, not a
matter of capacity or training. The readout (see
`src/models/transformer_model.py`, `TransformerForecastModel.forward`)
is a mean-pool across the 144-step input window followed by a linear
projection. Averaging the encoder output across the full window
destroys the most informative signal — the most recent timestep — by
mixing it with 143 increasingly stale ones. The training curves in
`training_curves_Area_*.png` show validation MSE plateauing cleanly
around epoch 10. The model was not underfit; it was converging to a
poor hypothesis class. Switching to a last-timestep readout, or to
attention pooling weighted toward the end of the sequence, would
almost certainly close most of the gap to SARIMA. This is the main
design lesson from the experiment.

**Why LSTM ties with persistence.** The LSTM's last-timestep readout
gives it access to the lag-1 signal, so it does not suffer the same
architectural failure as the Transformer. But with a 144-step input
window and roughly 660 k parameters, the optimiser can settle on a
smoother hypothesis than is optimal. Cutting the input window to about
12 lags (two hours) would likely push the model toward a sharper
lag-1 dependence, but I did not test this configuration.

**Worst time of day.** From `outputs/figures/hourly_mae_*.png`, both
neural models have their largest errors in the evening peak hours
(19:00–22:00) on cell 5161, the steepest part of the daily ramp.
SARIMA's hourly errors are nearly flat by comparison. This matches the
architectural analysis above: smoothed predictors hurt most when the
signal moves fastest.

**Worst day of week.** See `dow_mae.png`. Saturday and Sunday show
elevated error for the neural models on cell 5161 (weekend traffic
patterns differ from the weekday-dominant training set). SARIMA
absorbs this through its first-order differencing.

**Error CDF.** See `error_cdf.png` (cell 5161). SARIMA's CDF dominates
persistence's across the whole distribution. The LSTM dominates above
the median but has fatter tails. The Transformer is uniformly worse.
This rules out the alternative reading that "the LSTM is competitive
on average but has bad tails" and confirms the ranking from §IV.F at
every quantile.

**Possible improvements.**

1. A Transformer with a last-timestep readout, or with attention pooling weighted toward the end of the sequence.
2. An LSTM with a shorter input window (≤ 24 lags, i.e. four hours) to bias the model toward short-range dynamics.
3. SARIMAX with calendar, holiday, or event-flag exogenous regressors to absorb residual spikes.
4. Per-cell hyperparameter tuning instead of one config picked on the top-traffic cell.

---

## V. Reproducibility

```powershell
# One-button (Windows)
.\scripts\run_everything.ps1
```

```bash
# Linux / macOS / WSL / git-bash
./scripts/run_everything.sh
```

Each script is idempotent and resumable. The full pipeline took about
4 h 30 min on this hardware. The breakdown: data download about 25 min,
Parquet conversion about 4 min, EDA 30 s, model training and inference
4 h 9 min, reporting 34 s. SARIMA's walk-forward inference is the
single dominant cost (91 s × 3 cells in `predict_sarima`).

The neural hyperparameter search is seeded
(`tuning.random_search_neural(seed=0)`), and SARIMA is deterministic
given its order. The final neural training runs are not seeded beyond
NumPy and PyTorch defaults, so re-runs may drift by about ±5 % on MAE.
The ranking between models is robust to this drift.

The repository layout follows `README.md`. Figures are in
`outputs/figures/`, tables in `outputs/tables/`, and model checkpoints
and pickled results in `outputs/models/`.

---

## VI. References

[1] G. Barlacchi *et al.*, "A multi-source dataset of urban life in the
city of Milan and the Province of Trentino," *Scientific Data*, 2015.

[2] A. Vaswani *et al.*, "Attention Is All You Need," *NeurIPS*, 2017.

[3] S. Hochreiter and J. Schmidhuber, "Long Short-Term Memory," *Neural
Computation*, vol. 9, no. 8, pp. 1735–1780, 1997.

[4] G. E. P. Box, G. M. Jenkins, G. C. Reinsel, G. M. Ljung, *Time Series
Analysis: Forecasting and Control*, 5th ed., Wiley, 2015.

[5] D. A. Dickey and W. A. Fuller, "Distribution of the estimators for
autoregressive time series with a unit root," *J. Amer. Statist. Assoc.*,
vol. 74, no. 366a, pp. 427–431, 1979.
