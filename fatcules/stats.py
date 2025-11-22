from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
import math
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Wedge


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
    # Deprecated in favor of dashboard gauges; kept for compatibility.
    return build_dashboard({})


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


def _draw_gauge(ax: plt.Axes, label: str, rate: float | None) -> None:
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(label, fontsize=16, pad=10, color="#333")
    start_angle = 310  # left
    arc_span = 280
    end_angle = start_angle + arc_span

    # Green zone (0-75%)
    green_start_angle = start_angle + (arc_span * 0.25)
    green_end_angle = end_angle
    ax.add_patch(
        Wedge((0.5, 0.5), 0.5, green_start_angle, green_end_angle, width=0.18, facecolor="#7dff8a51", edgecolor="none")
    )
    # Red zone (75-100%)
    red_start_angle = start_angle
    red_end_angle = start_angle + (arc_span * 0.25)
    ax.add_patch(
        Wedge((0.5, 0.5), 0.5, red_start_angle, red_end_angle, width=0.18, facecolor="#fa847751", edgecolor="none")
    )

    # Fill Red value (in %)
    red_value_start_angle = start_angle + (arc_span * (1 - rate))
    red_value_end_angle = end_angle
    ax.add_patch(
        Wedge((0.5, 0.5), 0.47, red_value_start_angle, red_value_end_angle, width=0.12, facecolor="#C50000FF", edgecolor="none")
    )

    # Green Value (in %)
    green_rate = min(0.75, rate)
    green_value_start_angle = start_angle + (arc_span * (1 - green_rate))
    green_value_end_angle = end_angle
    ax.add_patch(
        Wedge((0.5, 0.5), 0.47, green_value_start_angle, green_value_end_angle, width=0.12, facecolor="#00B415FD", edgecolor="none")
    )

    # Gauge
    gauge_start_angle = start_angle + (arc_span * (1 - rate)) - 2
    gauge_end_angle = start_angle + (arc_span * (1 - rate))
    ax.add_patch(
        Wedge((0.5, 0.5), 0.50, gauge_start_angle, gauge_end_angle, width=0.45, facecolor="#111111BB", edgecolor="none")
    )
    ax.text(0.5, 0.1, "{:.2f}".format(rate * 100) + "%", ha="center", va="center", fontsize=28, fontweight="bold", color="#333")


def build_dashboard(fat_loss_rates: dict[int, float | None]) -> io.BytesIO:
    fig, axes = plt.subplots(1, 2, figsize=(8, 5))
    fig.patch.set_facecolor("white")
    labels = [("7-day fat loss rate", fat_loss_rates.get(7)), ("30-day fat loss rate", fat_loss_rates.get(30))]
    for ax, (label, rate) in zip(axes, labels):
        _draw_gauge(ax, label, rate)
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    buffer.seek(0)
    return buffer
