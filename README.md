# Fatcules Telegram Bot

Python Telegram bot for tracking weight and fat percentage using aiogram v3 and SQLite.

## Quick start
- Copy `.env.example` to `.env` and set `BOT_TOKEN`.
- Create and activate a virtual environment.
- Install dependencies: `pip install -r requirements.txt`.
- Run the bot: `python main.py`.

## Notes
- Data is stored in `./data/fatcules.db` (configurable via `DATABASE_PATH`).
- Commands/buttons: Add entry, Edit entry, Remove entry, Stats, and /start to reset.
- `.env` is auto-loaded at startup if present.
