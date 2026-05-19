"""
src/utils/timer.py
------------------
Utilities for measuring and reporting model training and inference time.
"""

import time
import platform
import torch
from contextlib import contextmanager
from typing import Optional


@contextmanager
def timer(label: str = ""):
    """Context manager that prints elapsed time."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"[Timer] {label}: {elapsed:.4f}s")


class ModelTimer:
    """Tracks and stores training and inference times for a model."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.train_time: Optional[float] = None
        self.inference_time: Optional[float] = None

    def start_train(self):
        self._train_start = time.perf_counter()

    def stop_train(self):
        self.train_time = time.perf_counter() - self._train_start

    def start_inference(self):
        self._inf_start = time.perf_counter()

    def stop_inference(self):
        self.inference_time = time.perf_counter() - self._inf_start

    def report(self) -> dict:
        return {
            "model": self.model_name,
            "train_time_s": round(self.train_time, 4) if self.train_time else None,
            "inference_time_s": round(self.inference_time, 4) if self.inference_time else None,
        }


def get_hardware_info() -> dict:
    """Return basic hardware information for reproducibility reporting."""
    info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cuda_available": torch.cuda.is_available(),
    }
    if torch.cuda.is_available():
        info["gpu"] = torch.cuda.get_device_name(0)
        info["cuda_version"] = torch.version.cuda
    return info
