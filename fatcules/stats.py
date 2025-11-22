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
    return build_dashboard({}, series)


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

# Do not change this method
def _draw_gauge(ax: plt.Axes, label: str, rate: float | None) -> None:
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(label, fontsize=16, pad=10, color="#333")
    base_radius = 0.5
    start_angle = 310  # left
    arc_span = 280
    end_angle = start_angle + arc_span

    # Green zone (0-75%)
    green_start_angle = start_angle + (arc_span * 0.25)
    green_end_angle = end_angle
    ax.add_patch(
        Wedge((0.5, 0.5), base_radius, green_start_angle, green_end_angle, width=0.18, facecolor="#7dff8a51", edgecolor="none")
    )
    # Red zone (75-100%)
    red_start_angle = start_angle
    red_end_angle = start_angle + (arc_span * 0.25)
    ax.add_patch(
        Wedge((0.5, 0.5), base_radius, red_start_angle, red_end_angle, width=0.18, facecolor="#fa847751", edgecolor="none")
    )

    # Fill Red value (in %)
    red_value_start_angle = start_angle + (arc_span * (1 - rate))
    red_value_end_angle = end_angle
    ax.add_patch(
        Wedge((0.5, 0.5), base_radius - 0.03, red_value_start_angle, red_value_end_angle, width=0.12, facecolor="#C50000FF", edgecolor="none")
    )

    # Green Value (in %)
    green_rate = min(0.75, rate)
    green_value_start_angle = start_angle + (arc_span * (1 - green_rate))
    green_value_end_angle = end_angle
    ax.add_patch(
        Wedge((0.5, 0.5), base_radius - 0.03, green_value_start_angle, green_value_end_angle, width=0.12, facecolor="#00B415FD", edgecolor="none")
    )

    # Gauge
    gauge_start_angle = start_angle + (arc_span * (1 - rate)) - 2
    gauge_end_angle = start_angle + (arc_span * (1 - rate))
    ax.add_patch(
        Wedge((0.5, 0.5), base_radius, gauge_start_angle, gauge_end_angle, width=0.45, facecolor="#111111BB", edgecolor="none")
    )
    ax.text(0.5, 0.1, "{:.2f}".format(rate * 100) + "%", ha="center", va="center", fontsize=16, fontweight="bold", color="#333")


def build_dashboard(
    fat_loss_rates: dict[int, float | None], series: Sequence[tuple[datetime, float]] | None = None
) -> io.BytesIO:
    fig = plt.figure(figsize=(8, 8))
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.2], hspace=0.55)

    gauges = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
    labels = [("7-day fat loss rate", fat_loss_rates.get(7)), ("30-day fat loss rate", fat_loss_rates.get(30))]
    for ax, (label, rate) in zip(gauges, labels):
        _draw_gauge(ax, label, rate)

    line_ax = fig.add_subplot(gs[1, :])
    if series:
        dates = [dt for dt, _ in series]
        values = [val for _, val in series]
        line_ax.plot(dates, values, marker="o", linewidth=2, color="#1f77b4")
        line_ax.set_xlim(min(dates), max(dates))
        line_ax.grid(True, linestyle="--", alpha=0.4)
        line_ax.set_xlabel("Date")
        line_ax.set_ylabel("Fat weight (kg)")
        line_ax.set_title("Fat weight over time", fontsize=12, color="#333")
        fig.autofmt_xdate(rotation=25, ha="right")
    else:
        line_ax.axis("off")
        line_ax.text(0.5, 0.5, "Add entries with fat % to see a graph", ha="center", va="center", fontsize=12)

    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    buffer.seek(0)
    return buffer
