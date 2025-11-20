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
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(dates, values, marker="o", linewidth=2)
    ax.set_title("Fat weight over time")
    ax.set_ylabel("kg")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.autofmt_xdate(rotation=30, ha="right")
    ax.text(
        0.02,
        0.98,
        summary,
        ha="left",
        va="top",
        transform=ax.transAxes,
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#f7f7f7", alpha=0.8),
    )
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return buffer
