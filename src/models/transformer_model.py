"""
src/models/transformer_model.py
--------------------------------
Transformer-based model for one-step-ahead traffic forecasting.

Architecture:
  Input → Linear projection → Positional Encoding
        → TransformerEncoder (N layers, multi-head attention)
        → Global average pooling → Linear → Output (1 value)

The Transformer captures long-range dependencies via self-attention,
and does not rely on sequential processing like RNNs.
"""

import math
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from src.utils.metrics import evaluate_all
from src.utils.timer import ModelTimer


# ── Default hyperparameters ────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "seq_length":   144,
    "d_model":      64,     # Embedding dimension (must be divisible by nhead)
    "nhead":        4,      # Number of attention heads
    "num_layers":   2,      # Transformer encoder layers
    "dim_feedforward": 256,
    "dropout":      0.1,
    "batch_size":   64,
    "epochs":       30,
    "lr":           1e-3,
}


class PositionalEncoding(nn.Module):
    """
    Standard sinusoidal positional encoding (Vaswani et al., 2017).
    Adds position information to the token embeddings.
    """

    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_len, d_model)
        pos = torch.arange(0, max_len).unsqueeze(1).float()
        div = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x):
        # x: (batch, seq_len, d_model)
        x = x + self.pe[:, : x.size(1)]
        return self.dropout(x)


class TransformerForecastModel(nn.Module):
    """Transformer encoder for univariate time series forecasting."""

    def __init__(self, d_model=64, nhead=4, num_layers=2,
                 dim_feedforward=256, dropout=0.1):
        super().__init__()
        self.input_proj = nn.Linear(1, d_model)
        self.pos_enc    = PositionalEncoding(d_model, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(d_model, 1)

    def forward(self, x):
        # x: (batch, seq_len, 1)
        x = self.input_proj(x)          # → (batch, seq_len, d_model)
        x = self.pos_enc(x)
        x = self.encoder(x)             # → (batch, seq_len, d_model)
        x = x.mean(dim=1)               # Global average pooling
        return self.fc(x).squeeze(-1)   # → (batch,)


def build_dataloaders(X_train, y_train, batch_size=64, val_split=0.1):
    split = int(len(X_train) * (1 - val_split))
    X_tr, X_val = X_train[:split], X_train[split:]
    y_tr, y_val = y_train[:split], y_train[split:]

    def to_loader(X, y, shuffle):
        X_t = torch.tensor(X).unsqueeze(-1)
        y_t = torch.tensor(y)
        return DataLoader(TensorDataset(X_t, y_t), batch_size=batch_size, shuffle=shuffle)

    return to_loader(X_tr, y_tr, True), to_loader(X_val, y_val, False)


def train_transformer(
    X_train: np.ndarray,
    y_train: np.ndarray,
    config: dict = DEFAULT_CONFIG,
    device: str = None,
    model_name: str = "Transformer",
) -> dict:
    """Train the Transformer model."""
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training Transformer on: {device}")

    model = TransformerForecastModel(
        d_model=config["d_model"],
        nhead=config["nhead"],
        num_layers=config["num_layers"],
        dim_feedforward=config["dim_feedforward"],
        dropout=config["dropout"],
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=config["lr"])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3)
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

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                val_loss += criterion(model(xb), yb).item()

        tl = epoch_loss / len(train_loader)
        vl = val_loss / len(val_loader)
        train_losses.append(tl)
        val_losses.append(vl)
        scheduler.step(vl)

        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1}/{config['epochs']} — "
                  f"Train Loss: {tl:.6f} | Val Loss: {vl:.6f}")

    t.stop_train()
    return {"model": model, "timer": t,
            "train_losses": train_losses, "val_losses": val_losses, "device": device}


def predict_transformer(fitted: dict, X_test: np.ndarray, scaler) -> np.ndarray:
    """Generate and inverse-transform predictions."""
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


def run_transformer(
    X_train, y_train, X_test, y_test_orig,
    scaler, config=DEFAULT_CONFIG,
) -> dict:
    """Full Transformer pipeline: train → predict → evaluate."""
    fitted = train_transformer(X_train, y_train, config)
    predictions = predict_transformer(fitted, X_test, scaler)
    metrics = evaluate_all(y_test_orig, predictions)

    print(f"\nTransformer Metrics → MAE: {metrics['MAE']:.4f} | "
          f"MAPE: {metrics['MAPE']:.2f}% | RMSE: {metrics['RMSE']:.4f}")

    return {"predictions": predictions, "metrics": metrics,
            "timer": fitted["timer"], "losses": fitted["train_losses"]}
