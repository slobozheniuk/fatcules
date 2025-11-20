from __future__ import annotations

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class EntryRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> aiosqlite.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA foreign_keys=ON;")
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL,
                    weight_kg REAL NOT NULL,
                    fat_pct REAL,
                    fat_weight_kg REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entries_user_time ON entries (user_id, recorded_at)"
            )
            await self._conn.commit()
        return self._conn

    async def add_entry(
        self, user_id: int, recorded_at: datetime, weight_kg: float, fat_pct: Optional[float]
    ) -> int:
        conn = await self.connect()
        fat_weight = weight_kg * fat_pct / 100 if fat_pct is not None else None
        cursor = await conn.execute(
            """
            INSERT INTO entries (user_id, recorded_at, weight_kg, fat_pct, fat_weight_kg)
            VALUES (:user_id, :recorded_at, :weight_kg, :fat_pct, :fat_weight_kg)
            """,
            {
                "user_id": user_id,
                "recorded_at": recorded_at.isoformat(),
                "weight_kg": weight_kg,
                "fat_pct": fat_pct,
                "fat_weight_kg": fat_weight,
            },
        )
        await conn.commit()
        return cursor.lastrowid

    async def update_entry(
        self, entry_id: int, user_id: int, weight_kg: float, fat_pct: Optional[float]
    ) -> bool:
        conn = await self.connect()
        fat_weight = weight_kg * fat_pct / 100 if fat_pct is not None else None
        cursor = await conn.execute(
            """
            UPDATE entries
            SET weight_kg = :weight_kg, fat_pct = :fat_pct, fat_weight_kg = :fat_weight_kg
            WHERE id = :entry_id AND user_id = :user_id
            """,
            {
                "entry_id": entry_id,
                "user_id": user_id,
                "weight_kg": weight_kg,
                "fat_pct": fat_pct,
                "fat_weight_kg": fat_weight,
            },
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def delete_entry(self, entry_id: int, user_id: int) -> bool:
        conn = await self.connect()
        cursor = await conn.execute(
            "DELETE FROM entries WHERE id = :entry_id AND user_id = :user_id",
            {"entry_id": entry_id, "user_id": user_id},
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def list_recent_entries(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        conn = await self.connect()
        cursor = await conn.execute(
            """
            SELECT id, user_id, recorded_at, weight_kg, fat_pct, fat_weight_kg
            FROM entries
            WHERE user_id = :user_id
            ORDER BY recorded_at DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit},
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_fat_weight_series(self, user_id: int) -> list[dict[str, Any]]:
        conn = await self.connect()
        cursor = await conn.execute(
            """
            SELECT recorded_at, fat_weight_kg
            FROM entries
            WHERE user_id = :user_id AND fat_weight_kg IS NOT NULL
            ORDER BY recorded_at ASC
            """,
            {"user_id": user_id},
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_latest_fat_weight(self, user_id: int) -> Optional[float]:
        conn = await self.connect()
        cursor = await conn.execute(
            """
            SELECT fat_weight_kg
            FROM entries
            WHERE user_id = :user_id AND fat_weight_kg IS NOT NULL
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            {"user_id": user_id},
        )
        row = await cursor.fetchone()
        return row["fat_weight_kg"] if row else None

