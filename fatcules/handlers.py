from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup

from .db import EntryRepository
from .formatting import format_entry_line, format_stats_summary, now_utc, parse_float
from .keyboards import (
    ADD_ENTRY,
    CANCEL,
    EDIT_ENTRY,
    REMOVE_ENTRY,
    SKIP_FAT,
    STATS,
    cancel_keyboard,
    fat_pct_keyboard,
    main_keyboard,
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
    data = await state.get_data()
    repo = get_repo(message)
    fat_pct = None
    if message.text == SKIP_FAT:
        fat_pct = None
    else:
        parsed = parse_float(message.text or "")
        if parsed is None or parsed <= 0:
            await message.answer("Please send a valid fat % or skip.", reply_markup=fat_pct_keyboard())
            return
        fat_pct = parsed
    recorded_at = now_utc()
    await repo.add_entry(
        user_id=message.from_user.id,  # type: ignore[arg-type]
        recorded_at=recorded_at,
        weight_kg=float(data["weight_kg"]),
        fat_pct=fat_pct,
    )
    await state.clear()
    fat_info = "" if fat_pct is None else f" and fat {fat_pct:.1f}%"
    await message.answer(
        f"Entry saved: {recorded_at.date()} {data['weight_kg']:.1f} kg{fat_info}",
        reply_markup=main_keyboard(),
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
    await state.update_data(entry_id=entry["id"])
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
    repo = get_repo(message)
    fat_pct = None
    if message.text == SKIP_FAT:
        fat_pct = None
    else:
        parsed = parse_float(message.text or "")
        if parsed is None or parsed <= 0:
            await message.answer("Please send a valid fat % or skip.", reply_markup=fat_pct_keyboard())
            return
        fat_pct = parsed
    updated = await repo.update_entry(
        entry_id=int(data["entry_id"]),
        user_id=message.from_user.id,  # type: ignore[arg-type]
        weight_kg=float(data["weight_kg"]),
        fat_pct=fat_pct,
    )
    await state.clear()
    if not updated:
        await message.answer("Could not update entry.", reply_markup=main_keyboard())
        return
    fat_info = "" if fat_pct is None else f" and fat {fat_pct:.1f}%"
    await message.answer(
        f"Entry updated: {data['weight_kg']:.1f} kg{fat_info}",
        reply_markup=main_keyboard(),
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
    await message.answer_photo(
        photo=plot_image,
        caption=summary_text,
        reply_markup=main_keyboard(),
    )
