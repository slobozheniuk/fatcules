from __future__ import annotations

from datetime import date, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


ADD_ENTRY = "Add entry"
EDIT_ENTRY = "Edit entries"
STATS = "Stats"
ADD_GOAL = "Add goal"
EDIT_GOAL = "Edit goal"
CANCEL = "Cancel"
SKIP_FAT = "Skip fat %"
DATEPICKER_PREFIX = "DP"
DUPLICATE_PREFIX = "DUP"
EDIT_PAGE_SIZE = 5
EDIT_PREV = "◀ Prev"
EDIT_NEXT = "Next ▶"
DELETE_ICON = "🗑"


def main_keyboard(goal_set: bool = False) -> ReplyKeyboardMarkup:
    goal_label = EDIT_GOAL if goal_set else ADD_GOAL
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADD_ENTRY), KeyboardButton(text=EDIT_ENTRY)],
            [KeyboardButton(text=STATS)],
            [KeyboardButton(text=goal_label)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose an action",
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL)]],
        resize_keyboard=True,
        input_field_placeholder="Type a value or cancel",
    )


def fat_pct_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=SKIP_FAT)], [KeyboardButton(text=CANCEL)]],
        resize_keyboard=True,
        input_field_placeholder="Send fat % or skip",
    )


def _start_of_month(day: date) -> date:
    return day.replace(day=1)


def _prev_month(day: date) -> date:
    first = _start_of_month(day)
    if first.month == 1:
        return first.replace(year=first.year - 1, month=12, day=1)
    return first.replace(month=first.month - 1, day=1)


def _next_month(day: date) -> date:
    first = _start_of_month(day)
    if first.month == 12:
        next_month_start = first.replace(year=first.year + 1, month=1, day=1)
    else:
        next_month_start = first.replace(month=first.month + 1, day=1)
    return next_month_start


def _callback(prefix: str, action: str, payload: str) -> str:
    return f"{DATEPICKER_PREFIX}|{prefix}|{action}|{payload}"


def datepicker_keyboard(prefix: str, month: date | None = None, default_date: date | None = None) -> InlineKeyboardMarkup:
    today = date.today()
    current_month = _start_of_month(month or today)
    header = [InlineKeyboardButton(text=current_month.strftime("%B %Y"), callback_data=_callback(prefix, "noop", "header"))]

    week_days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    weekday_row = [InlineKeyboardButton(text=day, callback_data=_callback(prefix, "noop", day.lower())) for day in week_days]

    first_weekday = current_month.weekday()
    days_in_month = (_next_month(current_month) - timedelta(days=1)).day
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []

    for _ in range(first_weekday):
        current_row.append(InlineKeyboardButton(text=" ", callback_data=_callback(prefix, "noop", "pad")))

    for day_num in range(1, days_in_month + 1):
        day_date = current_month.replace(day=day_num)
        current_row.append(
            InlineKeyboardButton(
                text=str(day_num),
                callback_data=_callback(prefix, "pick", day_date.isoformat()),
            )
        )
        if len(current_row) == 7:
            rows.append(current_row)
            current_row = []

    if current_row:
        while len(current_row) < 7:
            current_row.append(InlineKeyboardButton(text=" ", callback_data=_callback(prefix, "noop", "pad")))
        rows.append(current_row)

    nav_row = [
        InlineKeyboardButton(text="◀ Prev", callback_data=_callback(prefix, "nav", _prev_month(current_month).isoformat())),
        InlineKeyboardButton(text="Today", callback_data=_callback(prefix, "pick", today.isoformat())),
        InlineKeyboardButton(text="Next ▶", callback_data=_callback(prefix, "nav", _next_month(current_month).isoformat())),
    ]

    quick_row: list[InlineKeyboardButton] = []
    if default_date:
        quick_row.append(
            InlineKeyboardButton(
                text=f"Keep {default_date.isoformat()}",
                callback_data=_callback(prefix, "pick", default_date.isoformat()),
            )
        )

    keyboard = [header, weekday_row, *rows, nav_row]
    if quick_row:
        keyboard.append(quick_row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def parse_datepicker_data(data: str) -> tuple[str, str, str] | None:
    if not data or not data.startswith(f"{DATEPICKER_PREFIX}|"):
        return None
    parts = data.split("|", maxsplit=3)
    if len(parts) != 4:
        return None
    _, prefix, action, payload = parts
    return prefix, action, payload


def duplicate_date_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Replace existing",
                    callback_data=f"{DUPLICATE_PREFIX}|{prefix}|replace",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Choose different date",
                    callback_data=f"{DUPLICATE_PREFIX}|{prefix}|different",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Keep old data",
                    callback_data=f"{DUPLICATE_PREFIX}|{prefix}|keep",
                )
            ],
        ]
    )


def parse_duplicate_decision(data: str) -> tuple[str, str] | None:
    if not data or not data.startswith(f"{DUPLICATE_PREFIX}|"):
        return None
    parts = data.split("|", maxsplit=2)
    if len(parts) != 3:
        return None
    _, prefix, action = parts
    return prefix, action


def _entry_label(entry: dict) -> str:
    recorded_at = entry.get("recorded_at")
    weight = entry.get("weight_kg")
    fat = entry.get("fat_pct")
    date_text = recorded_at[:10] if isinstance(recorded_at, str) else str(recorded_at)
    base = f"{date_text}: {float(weight):.1f} kg" if weight is not None else str(entry)
    if fat is None:
        return base
    return f"{base}, fat {float(fat):.1f}%"


def edit_entries_keyboard(
    entries: list[dict], page: int = 0, page_size: int = EDIT_PAGE_SIZE
) -> ReplyKeyboardMarkup:
    total = len(entries)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = min(start + page_size, total)
    rows: list[list[KeyboardButton]] = []
    for idx, entry in enumerate(entries[start:end], start=start):
        rows.append(
            [
                KeyboardButton(text=f"{idx + 1}. {_entry_label(entry)}"),
                KeyboardButton(text=f"{DELETE_ICON}{idx + 1}"),
            ]
        )
    nav_row: list[KeyboardButton] = []
    if page > 0:
        nav_row.append(KeyboardButton(text=EDIT_PREV))
    nav_row.append(KeyboardButton(text=CANCEL))
    if page < total_pages - 1:
        nav_row.append(KeyboardButton(text=EDIT_NEXT))
    rows.append(nav_row)
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=f"Page {page + 1}/{total_pages}: tap an entry",
    )


def parse_edit_selection_text(text: str) -> tuple[str, int] | None:
    if text == EDIT_NEXT:
        return ("nav", 1)
    if text == EDIT_PREV:
        return ("nav", -1)
    if text == CANCEL:
        return ("cancel", 0)
    if text.startswith(DELETE_ICON):
        stripped = text.replace(DELETE_ICON, "", 1).strip()
        try:
            idx = int(stripped) - 1
        except ValueError:
            return None
        return ("delete", idx)
    parts = text.split(".", maxsplit=1)
    try:
        idx = int(parts[0]) - 1
    except (ValueError, IndexError):
        return None
    return ("pick", idx)
