from __future__ import annotations

from datetime import date, datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message, ReplyKeyboardMarkup

from .db import EntryRepository
from .formatting import format_entry_line, format_stats_summary, parse_float
from .keyboards import (
    ADD_ENTRY,
    CANCEL,
    DATEPICKER_PREFIX,
    EDIT_ENTRY,
    REMOVE_ENTRY,
    SKIP_FAT,
    STATS,
    cancel_keyboard,
    fat_pct_keyboard,
    main_keyboard,
    datepicker_keyboard,
    parse_datepicker_data,
)
from .states import AddEntryState, EditEntryState, RemoveEntryState
from .stats import average_daily_drop, build_plot, parse_series

router = Router()


def get_repo(message: Message) -> EntryRepository:
    repo = getattr(message.bot, "repo", None)
    if not isinstance(repo, EntryRepository):
        raise RuntimeError("Repository is not configured")
    return repo


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Hi! I track your weight and fat %. Use the buttons below.",
        reply_markup=main_keyboard(),
    )


@router.message(Command("cancel"))
@router.message(F.text == CANCEL)
async def cancel_any(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Cancelled. Choose next action.", reply_markup=main_keyboard())


@router.message(F.text == ADD_ENTRY)
async def add_entry_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AddEntryState.weight)
    await message.answer("Send weight in kg (e.g., 82.3).", reply_markup=cancel_keyboard())


@router.message(AddEntryState.weight)
async def add_entry_weight(message: Message, state: FSMContext) -> None:
    weight = parse_float(message.text or "")
    if weight is None or weight <= 0:
        await message.answer("Please send a valid weight number.", reply_markup=cancel_keyboard())
        return
    await state.update_data(weight_kg=weight)
    await state.set_state(AddEntryState.fat_pct)
    await message.answer(
        "Send fat % (e.g., 18.5) or tap skip.",
        reply_markup=fat_pct_keyboard(),
    )


@router.message(AddEntryState.fat_pct)
async def add_entry_fat(message: Message, state: FSMContext) -> None:
    fat_pct = None
    if message.text == SKIP_FAT:
        fat_pct = None
    else:
        parsed = parse_float(message.text or "")
        if parsed is None or parsed <= 0:
            await message.answer("Please send a valid fat % or skip.", reply_markup=fat_pct_keyboard())
            return
        fat_pct = parsed
    await state.update_data(fat_pct=fat_pct)
    await state.set_state(AddEntryState.date)
    await message.answer(
        "Pick a date (today is default). Use the calendar below or type Cancel.",
        reply_markup=datepicker_keyboard(prefix="add", month=date.today()),
    )


@router.message(F.text == EDIT_ENTRY)
async def edit_entry_start(message: Message, state: FSMContext) -> None:
    repo = get_repo(message)
    entries = await repo.list_recent_entries(user_id=message.from_user.id)  # type: ignore[arg-type]
    if not entries:
        await message.answer("No entries to edit yet.", reply_markup=main_keyboard())
        return
    lines = [format_entry_line(entry, index=i + 1) for i, entry in enumerate(entries)]
    await state.set_state(EditEntryState.choosing_entry)
    await state.update_data(entries=entries)
    await message.answer(
        "Pick an entry number to edit:\n" + "\n".join(lines),
        reply_markup=cancel_keyboard(),
    )


@router.message(EditEntryState.choosing_entry)
async def edit_entry_choose(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    entries = data.get("entries") or []
    selection = parse_float(message.text or "")
    if selection is None or int(selection) != selection:
        await message.answer("Send a number from the list.", reply_markup=cancel_keyboard())
        return
    idx = int(selection) - 1
    if idx < 0 or idx >= len(entries):
        await message.answer("Out of range. Try again.", reply_markup=cancel_keyboard())
        return
    entry = entries[idx]
    await state.update_data(entry_id=entry["id"], entry_recorded_at=entry["recorded_at"])
    await state.set_state(EditEntryState.weight)
    await message.answer(
        f"Send new weight for {format_entry_line(entry)}",
        reply_markup=cancel_keyboard(),
    )


@router.message(EditEntryState.weight)
async def edit_entry_weight(message: Message, state: FSMContext) -> None:
    weight = parse_float(message.text or "")
    if weight is None or weight <= 0:
        await message.answer("Please send a valid weight number.", reply_markup=cancel_keyboard())
        return
    await state.update_data(weight_kg=weight)
    await state.set_state(EditEntryState.fat_pct)
    await message.answer(
        "Send fat % (e.g., 18.5) or tap skip.",
        reply_markup=fat_pct_keyboard(),
    )


@router.message(EditEntryState.fat_pct)
async def edit_entry_fat(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    fat_pct = None
    if message.text == SKIP_FAT:
        fat_pct = None
    else:
        parsed = parse_float(message.text or "")
        if parsed is None or parsed <= 0:
            await message.answer("Please send a valid fat % or skip.", reply_markup=fat_pct_keyboard())
            return
        fat_pct = parsed
    await state.update_data(fat_pct=fat_pct)
    await state.set_state(EditEntryState.date)
    default_date = datetime.fromisoformat(data["entry_recorded_at"]).date()
    await message.answer(
        "Pick a date (defaults to the entry's current date). Use the calendar or type Cancel.",
        reply_markup=datepicker_keyboard(prefix="edit", month=default_date, default_date=default_date),
    )


@router.message(F.text == REMOVE_ENTRY)
async def remove_entry_start(message: Message, state: FSMContext) -> None:
    repo = get_repo(message)
    entries = await repo.list_recent_entries(user_id=message.from_user.id)  # type: ignore[arg-type]
    if not entries:
        await message.answer("No entries to remove.", reply_markup=main_keyboard())
        return
    lines = [format_entry_line(entry, index=i + 1) for i, entry in enumerate(entries)]
    await state.set_state(RemoveEntryState.choosing_entry)
    await state.update_data(entries=entries)
    await message.answer(
        "Pick an entry number to delete:\n" + "\n".join(lines),
        reply_markup=cancel_keyboard(),
    )


@router.message(RemoveEntryState.choosing_entry)
async def remove_entry_choose(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    entries = data.get("entries") or []
    selection = parse_float(message.text or "")
    if selection is None or int(selection) != selection:
        await message.answer("Send a number from the list.", reply_markup=cancel_keyboard())
        return
    idx = int(selection) - 1
    if idx < 0 or idx >= len(entries):
        await message.answer("Out of range. Try again.", reply_markup=cancel_keyboard())
        return
    entry = entries[idx]
    repo = get_repo(message)
    deleted = await repo.delete_entry(entry_id=entry["id"], user_id=message.from_user.id)  # type: ignore[arg-type]
    await state.clear()
    if not deleted:
        await message.answer("Could not delete entry.", reply_markup=main_keyboard())
        return
    await message.answer(f"Deleted: {format_entry_line(entry)}", reply_markup=main_keyboard())


@router.message(F.text == STATS)
async def stats(message: Message, state: FSMContext) -> None:
    await state.clear()
    repo = get_repo(message)
    raw_series = await repo.get_fat_weight_series(user_id=message.from_user.id)  # type: ignore[arg-type]
    if not raw_series:
        await message.answer("Need at least one entry with fat % to show stats.", reply_markup=main_keyboard())
        return
    series = parse_series(raw_series)
    drops = {days: average_daily_drop(series, days) for days in (7, 14, 30)}
    latest = await repo.get_latest_fat_weight(user_id=message.from_user.id)  # type: ignore[arg-type]
    summary_text = format_stats_summary(latest, drops)
    plot_image = build_plot(series, summary_text)
    photo = BufferedInputFile(plot_image.getvalue(), filename="fat-weight.png")
    await message.answer_photo(
        photo=photo,
        caption=summary_text,
        reply_markup=main_keyboard(),
    )


def _combine_date(selected: date) -> datetime:
    return datetime.combine(selected, datetime.min.time(), tzinfo=timezone.utc)


@router.callback_query(F.data.startswith(f"{DATEPICKER_PREFIX}|add|"))
async def add_entry_datepicker(callback: CallbackQuery, state: FSMContext) -> None:
    parsed = parse_datepicker_data(callback.data or "")
    if not parsed:
        await callback.answer()
        return
    prefix, action, payload = parsed
    if prefix != "add":
        await callback.answer()
        return
    current_state = await state.get_state()
    if current_state != AddEntryState.date.state:
        await callback.answer()
        return
    if action == "nav":
        target_month = date.fromisoformat(payload)
        await callback.message.edit_reply_markup(reply_markup=datepicker_keyboard(prefix="add", month=target_month))
        await callback.answer()
        return
    if action != "pick":
        await callback.answer()
        return
    selected_date = date.fromisoformat(payload)
    data = await state.get_data()
    weight = data.get("weight_kg")
    if weight is None or callback.message is None:
        await state.clear()
        await callback.answer("Something went wrong. Please start again.", show_alert=True)
        return
    repo = get_repo(callback.message)
    fat_pct = data.get("fat_pct")
    recorded_at = _combine_date(selected_date)
    await repo.add_entry(
        user_id=callback.from_user.id,  # type: ignore[arg-type]
        recorded_at=recorded_at,
        weight_kg=float(weight),
        fat_pct=fat_pct if fat_pct is not None else None,
    )
    await state.clear()
    fat_info = "" if fat_pct is None else f" and fat {fat_pct:.1f}%"
    await callback.message.answer(
        f"Entry saved: {recorded_at.date()} {float(weight):.1f} kg{fat_info}",
        reply_markup=main_keyboard(),
    )
    await callback.answer("Saved")


@router.callback_query(F.data.startswith(f"{DATEPICKER_PREFIX}|edit|"))
async def edit_entry_datepicker(callback: CallbackQuery, state: FSMContext) -> None:
    parsed = parse_datepicker_data(callback.data or "")
    if not parsed:
        await callback.answer()
        return
    prefix, action, payload = parsed
    if prefix != "edit":
        await callback.answer()
        return
    current_state = await state.get_state()
    if current_state != EditEntryState.date.state:
        await callback.answer()
        return
    if action == "nav":
        target_month = date.fromisoformat(payload)
        default_date = datetime.fromisoformat((await state.get_data())["entry_recorded_at"]).date()
        await callback.message.edit_reply_markup(
            reply_markup=datepicker_keyboard(prefix="edit", month=target_month, default_date=default_date)
        )
        await callback.answer()
        return
    if action != "pick":
        await callback.answer()
        return
    selected_date = date.fromisoformat(payload)
    data = await state.get_data()
    if callback.message is None or "entry_id" not in data:
        await state.clear()
        await callback.answer("Something went wrong. Please start again.", show_alert=True)
        return
    repo = get_repo(callback.message)
    fat_pct = data.get("fat_pct")
    weight = data.get("weight_kg")
    if weight is None:
        await state.clear()
        await callback.answer("Missing weight. Please restart edit.", show_alert=True)
        return
    recorded_at = _combine_date(selected_date)
    updated = await repo.update_entry(
        entry_id=int(data["entry_id"]),
        user_id=callback.from_user.id,  # type: ignore[arg-type]
        recorded_at=recorded_at,
        weight_kg=float(weight),
        fat_pct=fat_pct if fat_pct is not None else None,
    )
    await state.clear()
    if not updated:
        await callback.message.answer("Could not update entry.", reply_markup=main_keyboard())
        await callback.answer()
        return
    fat_info = "" if fat_pct is None else f" and fat {fat_pct:.1f}%"
    await callback.message.answer(
        f"Entry updated: {recorded_at.date()} {float(weight):.1f} kg{fat_info}",
        reply_markup=main_keyboard(),
    )
    await callback.answer("Updated")
