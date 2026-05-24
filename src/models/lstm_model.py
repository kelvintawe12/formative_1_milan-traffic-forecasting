"""
LSTM (Long Short-Term Memory) model for one-step-ahead traffic forecasting.

Architecture:
  Input  → LSTM layers → Dropout → Linear → Output (1 value)

The LSTM uses gated memory cells to capture long-range temporal dependencies,
making it well-suited for sequences with daily and weekly seasonality.
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from src.utils.metrics import evaluate_all
from src.utils.timer import ModelTimer


# ── Default hyperparameters ────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "seq_length":   144,    # 1 day of 10-min intervals
    "hidden_size":  128,
    "num_layers":   2,
    "dropout":      0.2,
    "batch_size":   64,
    "epochs":       30,
    "lr":           1e-3,
}


class LSTMModel(nn.Module):
    """Stacked LSTM with dropout and a final linear projection."""

    def __init__(self, input_size=1, hidden_size=128, num_layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        # x: (batch, seq_len, 1)
        out, _ = self.lstm(x)
        out = self.dropout(out[:, -1, :])   # Take last timestep
        return self.fc(out).squeeze(-1)


def build_dataloaders(
    X_train: np.ndarray,
    y_train: np.ndarray,
    batch_size: int = 64,
    val_split: float = 0.1,
):
    """Build train and validation DataLoaders from numpy arrays."""
    split = int(len(X_train) * (1 - val_split))
    X_tr, X_val = X_train[:split], X_train[split:]
    y_tr, y_val = y_train[:split], y_train[split:]

    def to_loader(X, y, shuffle):
        X_t = torch.tensor(X).unsqueeze(-1)  # (N, seq, 1)
        y_t = torch.tensor(y)
        return DataLoader(TensorDataset(X_t, y_t), batch_size=batch_size, shuffle=shuffle)

    return to_loader(X_tr, y_tr, True), to_loader(X_val, y_val, False)


def train_lstm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    config: dict = DEFAULT_CONFIG,
    device: str = None,
    model_name: str = "LSTM",
) -> dict:
    """
    Train the LSTM model.

    Args:
        X_train, y_train: Sequence arrays from preprocessor.create_sequences()
        config:           Hyperparameter dictionary
        device:           'cuda' or 'cpu' (auto-detected if None)
        model_name:       Label for timing

    Returns:
        {"model": LSTMModel, "timer": ModelTimer, "train_losses": list}
    """
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training LSTM on: {device}")

    model = LSTMModel(
        hidden_size=config["hidden_size"],
        num_layers=config["num_layers"],
        dropout=config["dropout"],
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=config["lr"])
    criterion = nn.MSELoss()
    train_loader, val_loader = build_dataloaders(X_train, y_train, config["batch_size"])

    t = ModelTimer(model_name)
    t.start_train()
    train_losses, val_losses = [], []

    for epoch in range(config["epochs"]):
        model.train()
        epoch_loss = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item()

        # Validation
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                val_loss += criterion(model(xb), yb).item()

        train_losses.append(epoch_loss / len(train_loader))
        val_losses.append(val_loss / len(val_loader))

        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1}/{config['epochs']} — "
                  f"Train Loss: {train_losses[-1]:.6f} | Val Loss: {val_losses[-1]:.6f}")

    t.stop_train()
    return {"model": model, "timer": t,
            "train_losses": train_losses, "val_losses": val_losses, "device": device}


def predict_lstm(
    fitted: dict,
    X_test: np.ndarray,
    scaler,
) -> np.ndarray:
    """
    Generate predictions on the test sequences and inverse-transform to original scale.

    Args:
        fitted:  Output of train_lstm()
        X_test:  Test sequences (n_samples, seq_length)
        scaler:  Fitted MinMaxScaler for inverse transform

    Returns:
        Predictions in original traffic units
    """
    model  = fitted["model"]
    device = fitted["device"]
    t      = fitted["timer"]

    model.eval()
    t.start_inference()

    X_t = torch.tensor(X_test).unsqueeze(-1).to(device)
    with torch.no_grad():
        preds_scaled = model(X_t).cpu().numpy()

    t.stop_inference()
    return scaler.inverse_transform(preds_scaled.reshape(-1, 1)).flatten()


def run_lstm(
    X_train, y_train, X_test, y_test_orig,
    scaler, config=DEFAULT_CONFIG,
) -> dict:
    """Full LSTM pipeline: train → predict → evaluate."""
    fitted = train_lstm(X_train, y_train, config)
    predictions = predict_lstm(fitted, X_test, scaler)
    metrics = evaluate_all(y_test_orig, predictions)

    print(f"\nLSTM Metrics → MAE: {metrics['MAE']:.4f} | "
          f"MAPE: {metrics['MAPE']:.2f}% | RMSE: {metrics['RMSE']:.4f}")

    return {"predictions": predictions, "metrics": metrics,
            "timer": fitted["timer"], "losses": fitted["train_losses"]}
