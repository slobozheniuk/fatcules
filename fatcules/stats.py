from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def parse_series(raw_entries: Iterable[dict]) -> list[tuple[datetime, float]]:
    series: list[tuple[datetime, float]] = []
    for item in raw_entries:
        recorded_at = datetime.fromisoformat(item["recorded_at"])
        fat_weight = float(item["fat_weight_kg"])
        series.append((recorded_at, fat_weight))
    return series


def average_daily_drop(series: Sequence[tuple[datetime, float]], days: int) -> float | None:
    if not series:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    window = [(dt, value) for dt, value in series if dt >= cutoff]
    if len(window) < 2:
        return None
    start_dt, start_val = window[0]
    end_dt, end_val = window[-1]
    delta_days = (end_dt - start_dt).total_seconds() / 86400
    if delta_days <= 0:
        return None
    return (start_val - end_val) / delta_days


def build_plot(series: Sequence[tuple[datetime, float]], summary: str) -> io.BytesIO:
    dates = [dt for dt, _ in series]
    values = [val for _, val in series]
    # iPhone-like aspect ratio (~19.5:9) for a taller plot
    fig, ax = plt.subplots(figsize=(8, 13))
    ax.plot(dates, values, marker="o", linewidth=2)
    ax.set_title("Fat weight over time")
    ax.set_ylabel("kg")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.autofmt_xdate(rotation=30, ha="right")
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def compute_fat_loss_rate(raw_entries: Sequence[dict], target_days: int) -> float | None:
    if len(raw_entries) < 2:
        return None
    parsed: list[tuple[datetime, float, float]] = []
    for item in raw_entries:
        if item.get("fat_weight_kg") is None or item.get("weight_kg") is None:
            continue
        try:
            recorded_at = datetime.fromisoformat(item["recorded_at"])
        except Exception:
            continue
        parsed.append((recorded_at, float(item["fat_weight_kg"]), float(item["weight_kg"])))
    if len(parsed) < 2:
        return None
    parsed.sort(key=lambda x: x[0])
    latest_dt, latest_fat, latest_weight = parsed[-1]
    target_dt = latest_dt - timedelta(days=target_days)
    closest_idx = None
    closest_delta = None
    for idx, (dt, _, _) in enumerate(parsed[:-1]):
        delta = abs((dt - target_dt).total_seconds())
        if closest_delta is None or delta < closest_delta:
            closest_delta = delta
            closest_idx = idx
    if closest_idx is None:
        return None
    prev_dt, prev_fat, prev_weight = parsed[closest_idx]
    if prev_dt == latest_dt:
        return None
    weight_delta = prev_weight - latest_weight
    if weight_delta == 0:
        return None
    fat_delta = prev_fat - latest_fat
    return fat_delta / weight_delta
