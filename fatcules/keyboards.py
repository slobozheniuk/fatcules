from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


ADD_ENTRY = "Add entry"
EDIT_ENTRY = "Edit entry"
REMOVE_ENTRY = "Remove entry"
STATS = "Stats"
CANCEL = "Cancel"
SKIP_FAT = "Skip fat %"


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADD_ENTRY), KeyboardButton(text=EDIT_ENTRY)],
            [KeyboardButton(text=REMOVE_ENTRY), KeyboardButton(text=STATS)],
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

