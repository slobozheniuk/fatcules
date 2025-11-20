from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def parse_float(value: str) -> Optional[float]:
    cleaned = value.strip().replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def format_entry_line(entry: dict, index: int | None = None) -> str:
    recorded_at = datetime.fromisoformat(entry["recorded_at"]).date().isoformat()
    prefix = f"{index}. " if index is not None else ""
    fat_pct = entry["fat_pct"]
    fat_text = f", fat {fat_pct:.1f}%" if fat_pct is not None else ""
    return f"{prefix}{recorded_at}: {entry['weight_kg']:.1f} kg{fat_text}"


def format_stats_summary(latest_fat_weight: float | None, drops: dict[int, float | None]) -> str:
    lines: list[str] = []
    if latest_fat_weight is None:
        lines.append("No fat % entries yet to build stats.")
    else:
        lines.append(f"Current fat weight: {latest_fat_weight:.2f} kg")
    lines.append("Average fat-weight drop:")
    for days in (7, 14, 30):
        drop = drops.get(days)
        if drop is None:
            lines.append(f"- {days}d: not enough data")
        else:
            lines.append(f"- {days}d: {drop:.3f} kg/day")
    return "\n".join(lines)
