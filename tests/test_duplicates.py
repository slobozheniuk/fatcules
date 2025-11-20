from datetime import datetime, timezone
import os
import tempfile
import unittest
from pathlib import Path

from fatcules.db import EntryRepository


class EntryRepositoryDuplicateTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmpdir.name, "test.db")
        self.repo = EntryRepository(Path(db_path))  # type: ignore[arg-type]
        await self.repo.connect()

    async def asyncTearDown(self) -> None:
        if self.repo._conn:
            await self.repo._conn.close()
        self.tmpdir.cleanup()

    async def test_get_entry_by_date_finds_entry(self) -> None:
        recorded = datetime(2024, 1, 2, 12, tzinfo=timezone.utc)
        await self.repo.add_entry(user_id=1, recorded_at=recorded, weight_kg=80.0, fat_pct=20.0)

        found = await self.repo.get_entry_by_date(user_id=1, recorded_date=recorded.date())

        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found["weight_kg"], 80.0)
        self.assertEqual(datetime.fromisoformat(found["recorded_at"]).date(), recorded.date())

    async def test_replace_flow_updates_conflict(self) -> None:
        day1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        day2 = datetime(2024, 1, 2, tzinfo=timezone.utc)

        conflict_id = await self.repo.add_entry(user_id=1, recorded_at=day2, weight_kg=70.0, fat_pct=15.0)
        entry_id = await self.repo.add_entry(user_id=1, recorded_at=day1, weight_kg=72.0, fat_pct=16.0)

        updated = await self.repo.update_entry(
            entry_id=entry_id,
            user_id=1,
            recorded_at=day2,
            weight_kg=75.0,
            fat_pct=14.0,
        )
        self.assertTrue(updated)
        self.assertTrue(await self.repo.delete_entry(entry_id=conflict_id, user_id=1))

        final = await self.repo.get_entry_by_date(user_id=1, recorded_date=day2.date())
        self.assertIsNotNone(final)
        assert final is not None
        self.assertEqual(final["id"], entry_id)
        self.assertEqual(final["weight_kg"], 75.0)
        # only one entry should remain
        all_entries = await self.repo.list_recent_entries(user_id=1, limit=10)
        self.assertEqual(len(all_entries), 1)


if __name__ == "__main__":
    unittest.main()
