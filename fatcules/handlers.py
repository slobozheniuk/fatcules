from __future__ import annotations

from datetime import date, datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message, ReplyKeyboardMarkup

from .db import EntryRepository
from .formatting import format_entry_line, format_stats_summary, parse_float, parse_height_cm
from .keyboards import (
    ADD_ENTRY,
    ADD_GOAL,
    CANCEL,
    DATEPICKER_PREFIX,
    DUPLICATE_PREFIX,
    EDIT_PAGE_SIZE,
    EDIT_ENTRY,
    EDIT_GOAL,
    SKIP_FAT,
    STATS,
    cancel_keyboard,
    fat_pct_keyboard,
    main_keyboard,
    datepicker_keyboard,
    duplicate_date_keyboard,
    edit_entries_keyboard,
    parse_datepicker_data,
    parse_duplicate_decision,
    parse_edit_selection_text,
)
from .states import AddEntryState, EditEntryState, GoalState, SetHeightState
from .stats import build_dashboard, compute_fat_loss_rate, parse_series, project_goal_date

router = Router()


def _goal_set(user: dict) -> bool:
    return user.get("goal_weight_kg") is not None and user.get("goal_fat_pct") is not None


def get_repo(message: Message) -> EntryRepository:
    repo = getattr(message.bot, "repo", None)
    if not isinstance(repo, EntryRepository):
        raise RuntimeError("Repository is not configured")
    return repo


async def _show_edit_entries(
    message: Message,
    state: FSMContext,
    repo: EntryRepository,
    page: int = 0,
    prefix: str = "Pick an entry to edit or delete",
    entries: list[dict] | None = None,
) -> None:
    if entries is None:
        entries = await repo.list_recent_entries(user_id=message.from_user.id)  # type: ignore[arg-type]
    if not entries:
        await state.clear()
        await message.answer("No entries to edit.", reply_markup=await main_keyboard_for(message))
        return
    total_pages = max(1, (len(entries) + EDIT_PAGE_SIZE - 1) // EDIT_PAGE_SIZE)
    page = max(0, min(total_pages - 1, page))
    await state.clear()
    await state.set_state(EditEntryState.choosing_entry)
    await state.update_data(entries=entries, edit_page=page)
    await message.answer(
        f"{prefix} (page {page + 1}/{total_pages}):",
        reply_markup=edit_entries_keyboard(entries, page=page),
    )


async def _save_height(user_id: int, height: float, message: Message, state: FSMContext) -> None:
    repo = get_repo(message)
    await repo.set_user_height(user_id=user_id, height_cm=height)
    await state.clear()
    await message.answer(
        f"Saved height: {height:.1f} cm.",
        reply_markup=await main_keyboard_for(message),
    )


async def main_keyboard_for(message: Message | CallbackQuery) -> ReplyKeyboardMarkup:
    msg = message if isinstance(message, Message) else message.message
    if msg is None:
        return main_keyboard()
    try:
        repo = get_repo(msg)
        user = await repo.ensure_user(msg.from_user.id)  # type: ignore[arg-type]
        goal_set = _goal_set(user)
    except Exception:
        goal_set = False
    return main_keyboard(goal_set=goal_set)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    repo = get_repo(message)
    user = await repo.ensure_user(message.from_user.id)  # type: ignore[arg-type]
    await message.answer(
        "Hi! I track your weight and fat %. Use the buttons below.",
        reply_markup=await main_keyboard_for(message),
    )
    if user.get("height_cm") is None:
        await state.set_state(SetHeightState.entering)
        await message.answer(
            "Before we start, please send your height in cm (50-250). You can also use /set_height later.",
            reply_markup=cancel_keyboard(),
        )


@router.message(Command("set_height"))
async def set_height_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    parts = (message.text or "").split(maxsplit=1)
    provided = parts[1] if len(parts) > 1 else ""
    if provided:
        height = parse_height_cm(provided)
        if height is None:
            await state.set_state(SetHeightState.entering)
            await message.answer("Height must be between 50 and 250 cm. Send your height in cm.", reply_markup=cancel_keyboard())
            return
        await _save_height(message.from_user.id, height, message, state)  # type: ignore[arg-type]
        return
    await state.set_state(SetHeightState.entering)
    await message.answer("Send your height in cm (50-250).", reply_markup=cancel_keyboard())


@router.message(SetHeightState.entering)
async def set_height_value(message: Message, state: FSMContext) -> None:
    height = parse_height_cm(message.text or "")
    if height is None:
        await message.answer(
            "Please send a valid height in cm between 50 and 250.",
            reply_markup=cancel_keyboard(),
        )
        return
    await _save_height(message.from_user.id, height, message, state)  # type: ignore[arg-type]


@router.message(F.text.in_({ADD_GOAL, EDIT_GOAL}))
async def goal_start(message: Message, state: FSMContext) -> None:
    await state.set_state(GoalState.weight)
    await message.answer("Send goal weight in kg (e.g., 75).", reply_markup=cancel_keyboard())


@router.message(GoalState.weight)
async def goal_weight(message: Message, state: FSMContext) -> None:
    if message.text == CANCEL:
        await cancel_any(message, state)
        return
    weight = parse_float(message.text or "")
    if weight is None or weight <= 0:
        await message.answer("Please send a valid goal weight.", reply_markup=cancel_keyboard())
        return
    await state.update_data(goal_weight=weight)
    await state.set_state(GoalState.fat_pct)
    await message.answer("Send goal fat % (e.g., 18.5).", reply_markup=cancel_keyboard())


@router.message(GoalState.fat_pct)
async def goal_fat(message: Message, state: FSMContext) -> None:
    if message.text == CANCEL:
        await cancel_any(message, state)
        return
    fat_pct = parse_float(message.text or "")
    if fat_pct is None or fat_pct <= 0 or fat_pct > 100:
        await message.answer("Please send a valid fat % (0-100).", reply_markup=cancel_keyboard())
        return
    data = await state.get_data()
    weight = data.get("goal_weight")
    if weight is None:
        await state.clear()
        await message.answer("Missing goal weight. Please start again.", reply_markup=await main_keyboard_for(message))
        return
    repo = get_repo(message)
    await repo.set_user_goal(user_id=message.from_user.id, weight_kg=float(weight), fat_pct=float(fat_pct))  # type: ignore[arg-type]
    await state.clear()
    goal_fat_weight = float(weight) * float(fat_pct) / 100
    await message.answer(
        f"Goal saved: {float(weight):.1f} kg at {float(fat_pct):.1f}% (fat {goal_fat_weight:.2f} kg).",
        reply_markup=await main_keyboard_for(message),
    )


@router.message(Command("cancel"), StateFilter("*"))
@router.message(F.text == CANCEL, StateFilter("*"))
async def cancel_any(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Cancelled. Choose next action.", reply_markup=await main_keyboard_for(message))


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
    await _show_edit_entries(message, state, repo, page=0, prefix="Pick an entry to edit or delete")


@router.message(EditEntryState.choosing_entry)
async def edit_entry_choose(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    entries = data.get("entries") or []
    page = int(data.get("edit_page") or 0)
    parsed = parse_edit_selection_text(message.text or "")
    total_pages = max(1, (len(entries) + EDIT_PAGE_SIZE - 1) // EDIT_PAGE_SIZE)
    if parsed is None:
        await message.answer(
            "Use the keyboard buttons to pick, delete, or navigate entries.",
            reply_markup=edit_entries_keyboard(entries, page=page),
        )
        return
    action, value = parsed
    if action == "cancel":
        await state.clear()
        await message.answer("Cancelled. Choose next action.", reply_markup=await main_keyboard_for(message))
        return
    if action == "nav":
        page = max(0, min(total_pages - 1, page + value))
        await state.update_data(edit_page=page)
        await message.answer(
            f"Pick an entry to edit or delete (page {page + 1}/{total_pages}):",
            reply_markup=edit_entries_keyboard(entries, page=page),
        )
        return
    if action == "delete":
        if value < 0 or value >= len(entries):
            await message.answer("Out of range. Try again.", reply_markup=edit_entries_keyboard(entries, page=page))
            return
        entry = entries[value]
        repo = get_repo(message)
        deleted = await repo.delete_entry(entry_id=entry["id"], user_id=message.from_user.id)  # type: ignore[arg-type]
        if not deleted:
            await message.answer("Could not delete entry.", reply_markup=edit_entries_keyboard(entries, page=page))
            return
        await _show_edit_entries(
            message,
            state,
            repo,
            page=page,
            prefix=f"Deleted: {format_entry_line(entry)}. Pick an entry to edit or delete",
        )
        return
    if action == "pick":
        if value < 0 or value >= len(entries):
            await message.answer("Out of range. Try again.", reply_markup=edit_entries_keyboard(entries, page=page))
            return
        entry = entries[value]
        await state.update_data(entry_id=entry["id"], entry_recorded_at=entry["recorded_at"], entry_index=value)
        await state.set_state(EditEntryState.weight)
        await message.answer(
            f"Send new weight for {format_entry_line(entry)}",
            reply_markup=cancel_keyboard(),
        )
        return


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


@router.message(F.text == STATS)
async def stats(message: Message, state: FSMContext) -> None:
    await state.clear()
    repo = get_repo(message)
    raw_series = await repo.get_fat_weight_series(user_id=message.from_user.id)  # type: ignore[arg-type]
    if not raw_series:
        await message.answer("Need at least one entry with fat % to show stats.", reply_markup=await main_keyboard_for(message))
        return
    series = parse_series(raw_series)
    latest = await repo.get_latest_fat_weight(user_id=message.from_user.id)  # type: ignore[arg-type]
    user = await repo.ensure_user(message.from_user.id)  # type: ignore[arg-type]
    latest_weight = await repo.get_latest_weight(user_id=message.from_user.id)  # type: ignore[arg-type]
    latest_bmi = None
    height_cm = user.get("height_cm")
    if height_cm and latest_weight:
        height_m = float(height_cm) / 100
        if height_m > 0:
            latest_bmi = float(latest_weight) / (height_m * height_m)
    goal_tuple = None
    goal_fat_weight = None
    if user.get("goal_weight_kg") is not None and user.get("goal_fat_pct") is not None:
        goal_weight = float(user["goal_weight_kg"])
        goal_fat_pct = float(user["goal_fat_pct"])
        goal_fat_weight = goal_weight * goal_fat_pct / 100
        goal_tuple = (goal_weight, goal_fat_pct, goal_fat_weight)
    goal_projection_text = None
    if goal_fat_weight is not None:
        projected_date, reason = project_goal_date(series, goal_fat_weight)
        if projected_date:
            goal_projection_text = f"Expected day of achieving goal: {projected_date.isoformat()}"
        elif reason:
            goal_projection_text = f"Expected day of achieving goal: {reason}."
    fat_loss_rates = {days: compute_fat_loss_rate(raw_series, days) for days in (7, 30)}
    summary_text = format_stats_summary(latest, latest_bmi, fat_loss_rates, goal_tuple, goal_projection_text)
    plot_image = build_dashboard(fat_loss_rates, series, goal_fat_weight)
    photo = BufferedInputFile(plot_image.getvalue(), filename="fat-weight.png")
    await message.answer_photo(
        photo=photo,
        caption=summary_text,
        reply_markup=await main_keyboard_for(message),
    )


def _combine_date(selected: date) -> datetime:
    return datetime.combine(selected, datetime.min.time(), tzinfo=timezone.utc)


def _selected_date_from_state(data: dict) -> date:
    stored = data.get("selected_date")
    if not stored:
        raise ValueError("selected_date not set in state")
    return date.fromisoformat(stored)


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
    existing = await repo.get_entry_by_date(callback.from_user.id, selected_date)  # type: ignore[arg-type]
    if existing:
        await state.update_data(
            selected_date=selected_date.isoformat(),
            conflict_entry_id=existing["id"],
        )
        await state.set_state(AddEntryState.confirm_existing)
        await callback.message.answer(
            f"An entry already exists for {selected_date.isoformat()}:\n{format_entry_line(existing)}\n"
            "Replace it, pick another date, or keep the old data?",
            reply_markup=duplicate_date_keyboard(prefix="add"),
        )
        await callback.answer()
        return
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
        reply_markup=await main_keyboard_for(callback),
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
    page = int(data.get("edit_page") or 0)
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
    conflict = await repo.get_entry_by_date(callback.from_user.id, selected_date)  # type: ignore[arg-type]
    if conflict and conflict["id"] != data["entry_id"]:
        await state.update_data(
            selected_date=selected_date.isoformat(),
            conflict_entry_id=conflict["id"],
        )
        await state.set_state(EditEntryState.confirm_existing)
        await callback.message.answer(
            f"Another entry exists for {selected_date.isoformat()}:\n{format_entry_line(conflict)}\n"
            "Replace it, pick a different date, or keep the old data?",
            reply_markup=duplicate_date_keyboard(prefix="edit"),
        )
        await callback.answer()
        return
    recorded_at = _combine_date(selected_date)
    updated = await repo.update_entry(
        entry_id=int(data["entry_id"]),
        user_id=callback.from_user.id,  # type: ignore[arg-type]
        recorded_at=recorded_at,
        weight_kg=float(weight),
        fat_pct=fat_pct if fat_pct is not None else None,
    )
    updated_entries = data.get("entries") or []
    if updated_entries:
        # Replace the edited entry in the local list and keep ordering by recorded_at desc
        updated_entry_payload = {
            "id": int(data["entry_id"]),
            "user_id": callback.from_user.id,
            "recorded_at": recorded_at.isoformat(),
            "weight_kg": float(weight),
            "fat_pct": fat_pct if fat_pct is not None else None,
            "fat_weight_kg": (float(weight) * float(fat_pct) / 100) if fat_pct is not None else None,
        }
        updated_entries = [e for e in updated_entries if int(e["id"]) != int(data["entry_id"])]
        updated_entries.append(updated_entry_payload)
        updated_entries.sort(key=lambda e: e.get("recorded_at"), reverse=True)
    if not updated:
        await _show_edit_entries(
            callback.message,
            state,
            repo,
            page=page,
            prefix="Could not update entry. Pick an entry to edit or delete",
            entries=updated_entries or None,
        )
        await callback.answer()
        return
    fat_info = "" if fat_pct is None else f" and fat {fat_pct:.1f}%"
    await _show_edit_entries(
        callback.message,
        state,
        repo,
        page=page,
        prefix=f"Entry updated: {recorded_at.date()} {float(weight):.1f} kg{fat_info}. Pick an entry to edit or delete",
        entries=updated_entries or None,
    )
    await callback.answer("Updated")


@router.callback_query(F.data.startswith(f"{DUPLICATE_PREFIX}|add|"))
async def add_entry_duplicate_decision(callback: CallbackQuery, state: FSMContext) -> None:
    parsed = parse_duplicate_decision(callback.data or "")
    if not parsed:
        await callback.answer()
        return
    prefix, action = parsed
    if prefix != "add":
        await callback.answer()
        return
    if await state.get_state() != AddEntryState.confirm_existing.state:
        await callback.answer()
        return
    data = await state.get_data()
    weight = data.get("weight_kg")
    fat_pct = data.get("fat_pct")
    conflict_entry_id = data.get("conflict_entry_id")
    if weight is None or conflict_entry_id is None or callback.message is None:
        await state.clear()
        await callback.answer("Something went wrong. Please start again.", show_alert=True)
        return
    if action == "different":
        selected_date = _selected_date_from_state(data)
        await state.set_state(AddEntryState.date)
        await callback.message.answer(
            "Pick a different date.",
            reply_markup=datepicker_keyboard(prefix="add", month=selected_date),
        )
        await callback.answer()
        return
    if action == "keep":
        await state.clear()
        await callback.message.answer(
            "Kept the existing entry. Nothing was saved.",
            reply_markup=await main_keyboard_for(callback),
        )
        await callback.answer()
        return
    if action == "replace":
        repo = get_repo(callback.message)
        selected_date = _selected_date_from_state(data)
        recorded_at = _combine_date(selected_date)
        updated = await repo.update_entry(
            entry_id=int(conflict_entry_id),
            user_id=callback.from_user.id,  # type: ignore[arg-type]
            recorded_at=recorded_at,
            weight_kg=float(weight),
            fat_pct=fat_pct if fat_pct is not None else None,
        )
        await state.clear()
        if not updated:
            await callback.message.answer("Could not replace existing entry.", reply_markup=await main_keyboard_for(callback))
            await callback.answer()
            return
        fat_info = "" if fat_pct is None else f" and fat {fat_pct:.1f}%"
        await callback.message.answer(
            f"Entry replaced for {recorded_at.date()}: {float(weight):.1f} kg{fat_info}",
            reply_markup=await main_keyboard_for(callback),
        )
        await callback.answer("Replaced")


@router.callback_query(F.data.startswith(f"{DUPLICATE_PREFIX}|edit|"))
async def edit_entry_duplicate_decision(callback: CallbackQuery, state: FSMContext) -> None:
    parsed = parse_duplicate_decision(callback.data or "")
    if not parsed:
        await callback.answer()
        return
    prefix, action = parsed
    if prefix != "edit":
        await callback.answer()
        return
    if await state.get_state() != EditEntryState.confirm_existing.state:
        await callback.answer()
        return
    data = await state.get_data()
    entry_id = data.get("entry_id")
    conflict_entry_id = data.get("conflict_entry_id")
    weight = data.get("weight_kg")
    fat_pct = data.get("fat_pct")
    page = int(data.get("edit_page") or 0)
    if callback.message is None or entry_id is None or weight is None or conflict_entry_id is None:
        await state.clear()
        await callback.answer("Something went wrong. Please start again.", show_alert=True)
        return
    selected_date = _selected_date_from_state(data)
    if action == "different":
        await state.set_state(EditEntryState.date)
        await callback.message.answer(
            "Pick a different date.",
            reply_markup=datepicker_keyboard(prefix="edit", month=selected_date, default_date=selected_date),
        )
        await callback.answer()
        return
    if action == "keep":
        repo = get_repo(callback.message)
        await _show_edit_entries(
            callback.message,
            state,
            repo,
            page=page,
            prefix="Kept the existing entry. Pick an entry to edit or delete",
            entries=data.get("entries") or None,
        )
        await callback.answer()
        return
    if action == "replace":
        repo = get_repo(callback.message)
        recorded_at = _combine_date(selected_date)
        updated = await repo.update_entry(
            entry_id=int(entry_id),
            user_id=callback.from_user.id,  # type: ignore[arg-type]
            recorded_at=recorded_at,
            weight_kg=float(weight),
            fat_pct=fat_pct if fat_pct is not None else None,
        )
        if not updated:
            await _show_edit_entries(
                callback.message,
                state,
                repo,
                page=page,
                prefix="Could not update entry. Pick an entry to edit or delete",
                entries=data.get("entries") or None,
            )
            await callback.answer()
            return
        if int(conflict_entry_id) != int(entry_id):
            await repo.delete_entry(entry_id=int(conflict_entry_id), user_id=callback.from_user.id)  # type: ignore[arg-type]
        fat_info = "" if fat_pct is None else f" and fat {fat_pct:.1f}%"
        entries = data.get("entries") or []
        if entries:
            entries = [e for e in entries if int(e["id"]) != int(entry_id) and int(e["id"]) != int(conflict_entry_id)]
            entries.append(
                {
                    "id": int(entry_id),
                    "user_id": callback.from_user.id,
                    "recorded_at": recorded_at.isoformat(),
                    "weight_kg": float(weight),
                    "fat_pct": fat_pct if fat_pct is not None else None,
                    "fat_weight_kg": (float(weight) * float(fat_pct) / 100) if fat_pct is not None else None,
                }
            )
            entries.sort(key=lambda e: e.get("recorded_at"), reverse=True)
        await _show_edit_entries(
            callback.message,
            state,
            repo,
            page=page,
            prefix=(
                f"Entry updated for {recorded_at.date()}: {float(weight):.1f} kg{fat_info}. "
                "Replaced existing data. Pick an entry to edit or delete"
            ),
            entries=entries or None,
        )
        await callback.answer("Replaced")
