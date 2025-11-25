# Repository Guidelines

## Project Structure & Modules
- App entrypoint: `main.py` wires settings, database repository, and aiogram dispatcher/router.
- Bot logic: `fatcules/handlers.py` (FSM flows, commands), `fatcules/keyboards.py` (reply/inline keyboards), `fatcules/stats.py` (calculations + chart generation), `fatcules/formatting.py` (parsing/formatting), `fatcules/db.py` (SQLite queries), `fatcules/config.py` (env loading), `fatcules/states.py` (FSM states).
- Data: SQLite file at `data/fatcules.db` (override with `DATABASE_PATH`).
- Tests: `tests/` uses `unittest` with focused modules per feature.

## Setup, Build, and Local Run
- Create env: `python -m venv .venv && source .venv/bin/activate`.
- Install deps: `pip install -r requirements.txt`.
- Configure: copy `.env.example` → `.env`, set `BOT_TOKEN`, optional `DATABASE_PATH`.
- Run bot locally: `python main.py` (loads `.env` automatically).
- Docker: `docker build -t fatcules-bot .` then `docker run -d --name fatcules-bot --restart unless-stopped --env-file .env -v $(pwd)/data:/app/data fatcules-bot`.

## Coding Style & Naming
- Python, 4-space indentation, prefer type hints and `@dataclass` where helpful.
- Use snake_case for functions/variables, PascalCase for classes/states, ALL_CAPS for constants and keyboard labels.
- Keep handler coroutines small; push parsing/formatting into `formatting.py` or helper functions.
- Avoid silent failures: raise `RuntimeError` for missing config, validate user input before DB writes.

## Testing Guidelines
- Framework: stdlib `unittest`. Run all: `python -m unittest discover -s tests -p "test_*.py"`.
- Add targeted tests beside new modules; prefer deterministic inputs (e.g., fixed `datetime` with `timezone.utc`).
- When touching stats/formatting, assert both numeric precision and message text snippets.
- If introducing async logic, use async test helpers or wrap in event loop with care to avoid hanging bots.

## Commit & Pull Request Practices
- Recent history uses concise, imperative summaries (e.g., “Add goal projection feature”, “Update formatting…”). Follow that style.
- Commits should bundle related changes (code + tests); avoid mixing refactors with feature logic.
- PRs: describe user-facing change, list test commands run, mention env vars or DB migrations, and attach screenshots for UI-like keyboards or stats images if altered.

## Security & Configuration
- Keep `.env` out of version control; never log `BOT_TOKEN`. Use `DATABASE_PATH` to point to writable volumes in containers.
- Matplotlib and Pillow render charts; confirm fonts/images are available in the target environment when packaging Docker images.
