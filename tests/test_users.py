import os
from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path

from fatcules.db import EntryRepository


class UserRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmpdir.name, "test.db")
        self.repo = EntryRepository(Path(db_path))  # type: ignore[arg-type]
        await self.repo.connect()

    async def asyncTearDown(self) -> None:
        if self.repo._conn:
            await self.repo._conn.close()
        self.tmpdir.cleanup()

    async def test_ensure_user_creates_row(self) -> None:
        user = await self.repo.ensure_user(123)
        self.assertEqual(user["id"], 123)
        self.assertIsNone(user["height_cm"])

        fetched = await self.repo.get_user(123)
        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual(fetched["id"], 123)

    async def test_set_user_height_upserts(self) -> None:
        await self.repo.set_user_height(5, 180.0)
        user = await self.repo.get_user(5)
        self.assertIsNotNone(user)
        assert user is not None
        self.assertAlmostEqual(user["height_cm"], 180.0)

        await self.repo.set_user_height(5, 182.5)
        updated = await self.repo.get_user(5)
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertAlmostEqual(updated["height_cm"], 182.5)

    async def test_get_latest_weight(self) -> None:
        self.assertIsNone(await self.repo.get_latest_weight(42))
        await self.repo.add_entry(user_id=42, recorded_at=datetime(2024, 1, 1, tzinfo=timezone.utc), weight_kg=80.0, fat_pct=None)
        await self.repo.add_entry(user_id=42, recorded_at=datetime(2024, 1, 2, tzinfo=timezone.utc), weight_kg=81.0, fat_pct=None)

        latest = await self.repo.get_latest_weight(42)
        self.assertEqual(latest, 81.0)
        # ensure fat series includes weight
        series = await self.repo.get_fat_weight_series(42)
        self.assertTrue(all("weight_kg" in item for item in series))


if __name__ == "__main__":
    unittest.main()
