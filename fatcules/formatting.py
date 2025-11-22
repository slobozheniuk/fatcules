from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def parse_float(value: str) -> Optional[float]:
    cleaned = value.strip().replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_height_cm(value: str) -> Optional[float]:
    height = parse_float(value)
    if height is None:
        return None
    if 50 <= height <= 250:
        return height
    return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def format_entry_line(entry: dict, index: int | None = None) -> str:
    recorded_at = datetime.fromisoformat(entry["recorded_at"]).date().isoformat()
    prefix = f"{index}. " if index is not None else ""
    fat_pct = entry["fat_pct"]
    fat_text = f", fat {fat_pct:.1f}%" if fat_pct is not None else ""
    return f"{prefix}{recorded_at}: {entry['weight_kg']:.1f} kg{fat_text}"


def format_stats_summary(
    latest_fat_weight: float | None,
    latest_bmi: float | None = None,
    fat_loss_rates: dict[int, float | None] | None = None,
    goal: tuple[float, float, float] | None = None,
) -> str:
    lines: list[str] = []
    if latest_fat_weight is None:
        lines.append("No fat % entries yet to build stats.")
    else:
        lines.append(f"Current fat weight: {latest_fat_weight:.2f} kg")
    if latest_bmi is None:
        lines.append("Latest BMI: set height with /set_height")
    else:
        lines.append(f"Latest BMI: {latest_bmi:.1f}")
    if goal:
        weight, fat_pct, fat_weight = goal
        lines.append(f"Goal: {weight:.1f} kg @ {fat_pct:.1f}% (fat {fat_weight:.2f} kg)")
    if fat_loss_rates is not None:
        lines.append("Fat loss rate:")
        for days in (7, 30):
            rate = fat_loss_rates.get(days)
            if rate is None:
                lines.append(f"- {days}d: not enough data")
            else:
                lines.append(f"- {days}d: {rate:.3f} fat kg per kg weight")
    return "\n".join(lines)
