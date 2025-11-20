import unittest

from fatcules.keyboards import (
    EDIT_NEXT,
    EDIT_PREV,
    edit_entries_keyboard,
    parse_edit_selection_text,
)


class EditKeyboardTests(unittest.TestCase):
    def test_paginated_keyboard_limits_entries(self) -> None:
        entries = [
            {"recorded_at": f"2024-01-0{i}T00:00:00+00:00", "weight_kg": 70 + i, "fat_pct": None}
            for i in range(1, 9)
        ]
        kb = edit_entries_keyboard(entries, page=0, page_size=3)
        # first page contains first 3 entries and nav row
        self.assertEqual(len(kb.keyboard), 4)
        self.assertTrue(kb.keyboard[0][0].text.startswith("1. 2024-01-01"))
        self.assertIn("71.0", kb.keyboard[0][0].text)
        # nav row should include Cancel and Next
        nav_texts = [btn.text for btn in kb.keyboard[-1]]
        self.assertIn("Cancel", nav_texts)
        self.assertIn("Next ▶", nav_texts)

    def test_parse_edit_selection(self) -> None:
        self.assertEqual(parse_edit_selection_text("EDITSEL|pick|2"), None)
        self.assertEqual(parse_edit_selection_text(EDIT_NEXT), ("nav", 1))
        self.assertEqual(parse_edit_selection_text(EDIT_PREV), ("nav", -1))
        self.assertEqual(parse_edit_selection_text("3. 2024-01-03: 73.0 kg"), ("pick", 2))
        self.assertEqual(parse_edit_selection_text("Cancel"), ("cancel", 0))

    def test_second_page_numbering_and_nav(self) -> None:
        entries = [
            {"recorded_at": f"2024-01-{i:02d}T00:00:00+00:00", "weight_kg": 70 + i, "fat_pct": None}
            for i in range(1, 9)
        ]
        kb = edit_entries_keyboard(entries, page=1, page_size=3)
        # first row on second page should start with 4 (global index)
        self.assertTrue(kb.keyboard[0][0].text.startswith("4. 2024-01-04"))
        nav_texts = [btn.text for btn in kb.keyboard[-1]]
        self.assertIn(EDIT_PREV, nav_texts)
        self.assertIn("Cancel", nav_texts)


if __name__ == "__main__":
    unittest.main()
