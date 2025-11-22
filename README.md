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
  - Edit an entry (paginated custom keyboard to select which entry to edit).
  - Remove an entry (paginated custom keyboard to select which entry to delete).
  - Get statistics.
- If a date already has an entry, users choose to replace existing data, pick a different date, or keep the current entry.
- Statistics return a picture showing:
  - Fat weight (`total weight * fat percentage`).
  - Dashboard gauges for 7-day and 30-day fat loss rates.
  - Latest BMI (when height is set).
  - 7-day and 30-day fat loss rates (difference in fat weight over difference in body weight).
- Store measurements in a lightweight database.
- When adding or editing entries:
  - Date defaults to the current day but can be overridden so older values can be added or corrected.

## Notes
- Data is stored in `./data/fatcules.db` (configurable via `DATABASE_PATH`).
- `.env` is auto-loaded at startup if present.
- Commands/buttons: Add entry, Edit entry, Remove entry, Stats, and /start to reset.
- Height is stored per user; new users are prompted on /start to send height (50-250 cm) and it can be updated anytime with `/set_height <cm>`. Stats include latest BMI when height is set.
- Add/Edit flows show an inline date picker; today/entry date is preselected but any date can be chosen.
- Edit/Delete selection uses a paginated custom keyboard (Prev/Next) instead of inline buttons.
- Weight and fat inputs use a numpad-style custom keyboard; type digits then press Enter (fat input keeps a Skip button).

## Docker
Build and run the bot as a self-restarting container (mount `./data` for the SQLite DB and supply `BOT_TOKEN`):
- Build: `docker build -t fatcules-bot .`
- Run in background with restart: `docker run -d --name fatcules-bot --restart unless-stopped --env-file .env -v $(pwd)/data:/app/data fatcules-bot`
- Stop/start: `docker stop fatcules-bot` / `docker start fatcules-bot`

Place your .env in the project root (same folder as Dockerfile, main.py, etc.). When you run the container, point --env-file at that path (e.g., from the repo
  root: docker run ... --env-file .env ...). If you keep .env elsewhere on the Pi, just pass its full path to --env-file.
