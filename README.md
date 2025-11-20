# Fatcules Telegram Bot

Python Telegram bot for tracking weight and fat percentage using aiogram v3 and SQLite.

## Quick start
- Copy `.env.example` to `.env` and set `BOT_TOKEN`.
- Create and activate a virtual environment.
- Install dependencies: `pip install -r requirements.txt`.
- Run the bot: `python main.py`.

## Product requirements
- Virtual keyboard with buttons:
  - Add a new entry with weight and optionally fat percentage.
  - Edit an entry (numbered list to select which entry to edit).
  - Remove an entry (numbered list to select which entry to delete).
  - Get statistics.
- Statistics return a picture showing:
  - Fat weight (`total weight * fat percentage`).
  - Average drop in fat weight over the last 7, 14, and 30 days.
  - Graph of fat weight over time.
- Store measurements in a lightweight database.
- When adding or editing entries:
  - Date defaults to the current day but can be overridden so older values can be added or corrected.

## Notes
- Data is stored in `./data/fatcules.db` (configurable via `DATABASE_PATH`).
- `.env` is auto-loaded at startup if present.
- Commands/buttons: Add entry, Edit entry, Remove entry, Stats, and /start to reset.
- Add/Edit flows show an inline date picker; today/entry date is preselected but any date can be chosen.
