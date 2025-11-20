from aiogram.fsm.state import State, StatesGroup


class AddEntryState(StatesGroup):
    weight = State()
    fat_pct = State()
    date = State()
    confirm_existing = State()


class EditEntryState(StatesGroup):
    choosing_entry = State()
    weight = State()
    fat_pct = State()
    date = State()
    confirm_existing = State()


class RemoveEntryState(StatesGroup):
    choosing_entry = State()
