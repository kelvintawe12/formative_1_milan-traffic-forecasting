# Milan Mobile Network Traffic Forecasting

Comparative time series analysis and forecasting of mobile network traffic using the Telecom Italia Big Data Challenge dataset.

## Project Structure

```
milan-traffic-forecasting/
├── data/
│   ├── raw/                  # Original downloaded .txt files (not committed to git)
│   └── processed/            # Cleaned, optimized .parquet files
├── notebooks/
│   ├── 01_data_handling.ipynb       # Task 1: Loading & memory optimization
│   ├── 02_eda.ipynb                 # Task 2: Exploratory data analysis
│   ├── 03_models.ipynb              # Task 3: Model training & evaluation
│   └── 04_results_reporting.ipynb   # Task 3: Plots, tables, failure analysis
├── src/
│   ├── data/
│   │   ├── loader.py         # Data loading & memory optimization utilities
│   │   └── preprocessor.py   # Feature engineering & normalization
│   ├── eda/
│   │   ├── plots.py          # All EDA visualization functions
│   │   └── stats.py          # Stationarity, ACF/PACF, decomposition
│   ├── models/
│   │   ├── sarima_model.py   # SARIMA implementation
│   │   ├── lstm_model.py     # LSTM implementation (PyTorch)
│   │   └── transformer_model.py  # Transformer implementation (PyTorch)
│   └── utils/
│       ├── metrics.py        # MAE, MAPE, RMSE
│       └── timer.py          # Training/execution time tracking
├── outputs/
│   ├── figures/              # All saved plots (PNG)
│   ├── tables/               # CSV/LaTeX performance tables
│   └── models/               # Saved model checkpoints
├── reports/                  # Final report (PDF/LaTeX)
├── requirements.txt
├── environment.yml
└── README.md
```

## Setup

### Quick start — one button

```powershell
# Windows / PowerShell
.\scripts\run_everything.ps1
```

```bash
# Linux / macOS / WSL / git-bash
./scripts/run_everything.sh
```

This installs the venv, downloads the ~20 GB dataset from Harvard Dataverse,
runs a one-day smoke test, then executes all four notebooks end-to-end.
Every step is idempotent — re-running picks up where it left off. See
[`scripts/README.md`](scripts/README.md) for per-step usage and resume flags.

### Manual setup (if you'd rather drive each step)

#### 1. Clone the repo
```bash
git clone https://github.com/kelvintawe12/formative_1_milan-traffic-forecasting.git
cd milan-traffic-forecasting
```

#### 2. Create environment

Either via the helper script:
```powershell
.\scripts\00_setup_env.ps1            # creates .venv\
```
or by hand with conda:
```bash
conda env create -f environment.yml
conda activate milan-traffic
```

#### 3. Download the data

The raw release is **~20 GB** of tab-separated `.txt` files (one per day, 62 days
covering Nov 1 – Dec 31, 2013). It is hosted on Harvard Dataverse:

- **Telecommunications activity, Milan** (the only file set we need):
  <https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/EGZHFV>
- **Grid (Milan tessellation)** — only needed if you want to overlay the heatmap
  on geographic coordinates: <https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/QJWLFU>

**Automated:**
```powershell
.\scripts\01_download_data.ps1     # uses the Dataverse API, no clicks
```
```bash
./scripts/01_download_data.sh
```
The helper hits the public Dataverse API, streams each file, transparently
unzips/un-gz's archives, and is resumable on failure.

**Manual fallback:**
If the API path fails (rate-limit, guestbook gate), use the web UI at
<https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/EGZHFV>.
Unpack so the daily files sit directly under `data/raw/`:

```
data/raw/sms-call-internet-mi-2013-11-01.txt
data/raw/sms-call-internet-mi-2013-11-02.txt
...
data/raw/sms-call-internet-mi-2013-12-31.txt
```

> **Important:** the paper [Barlacchi et al., 2015] lists the field order
> incorrectly. The real order is
> `square_id <TAB> time_interval <TAB> country_code <TAB> sms_in <TAB> sms_out <TAB> call_in <TAB> call_out <TAB> internet_traffic`.
> `loader.py` already accounts for this.

Notebook `01_data_handling.ipynb` converts the 20 GB raw store into a Snappy
Parquet dataset under `data/processed/milan_traffic_parquet/` (one shard per
day, ~2 GB total). All later notebooks read selectively from this store —
the full dataset is never loaded into RAM.

#### 4. Run notebooks in order

```powershell
.\scripts\03_run_all.ps1            # or: python run_pipeline.py
```
```bash
./scripts/03_run_all.sh
```

Runs `01 → 02 → 03 → 04`. Plan for several hours wall-clock (SARIMA at
s=144 with walk-forward inference is the bottleneck). To resume after a
crash, pass `-Skip 01,02` (PowerShell) or `--skip 01 02` (bash).

## Models
| Model | Type | Library |
|---|---|---|
| SARIMA | Statistical | statsmodels |
| LSTM | Neural Network | PyTorch |
| Transformer | Neural Network | PyTorch |

## Evaluation Period
- **Test set:** December 16–22 (used for evaluation only, never for training)

## Hardware Used

- **OS:** Windows 11 Pro (build 10.0.22631)
- **CPU:** Intel Core i7 (Family 6, Model 186) — CPU-only run, no CUDA
- **Python:** 3.11.9
- **Key libraries:** pandas 3.0.3, pyarrow 24.0.0, statsmodels (SARIMAX),
  PyTorch 2.12.0 (CPU build), scikit-learn (MinMaxScaler).
- **Full pipeline wall time:** ~4 h 30 min end-to-end. Bottleneck is
  SARIMA walk-forward inference (~91 s × 3 cells).

## References

See `reports/REPORT.md` § VI for the full IEEE-style bibliography
(Barlacchi et al. 2015, Vaswani et al. 2017, Hochreiter & Schmidhuber
1997, Box–Jenkins, Dickey–Fuller).
