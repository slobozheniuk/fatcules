from dataclasses import dataclass
from pathlib import Path
import os
from typing import Iterable


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Settings:
    bot_token: str
    database_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        _load_env_file(Path(".env"))
        token = os.getenv("BOT_TOKEN")
        if not token:
            raise RuntimeError("BOT_TOKEN is not set")
        db_path = Path(os.getenv("DATABASE_PATH", "./data/fatcules.db"))
        return cls(bot_token=token, database_path=db_path)
