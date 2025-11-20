import unittest

from fatcules.keyboards import (
    EDIT_PAGE_SIZE,
    edit_entries_keyboard,
    parse_edit_selection_data,
)


class EditKeyboardTests(unittest.TestCase):
    def test_paginated_keyboard_limits_entries(self) -> None:
        entries = [
            {"recorded_at": f"2024-01-0{i}T00:00:00+00:00", "weight_kg": 70 + i, "fat_pct": None}
            for i in range(1, 9)
        ]
        kb = edit_entries_keyboard(entries, page=0, page_size=3)
        # first page contains first 3 entries and nav row
        self.assertEqual(len(kb.inline_keyboard), 4)
        self.assertIn("2024-01-01", kb.inline_keyboard[0][0].text)
        self.assertIn("71.0", kb.inline_keyboard[0][0].text)
        # nav row should include Next and page indicator
        nav_texts = [btn.text for btn in kb.inline_keyboard[-1]]
        self.assertIn("Next ▶", nav_texts)
        self.assertIn("1/3", nav_texts)

    def test_parse_edit_selection(self) -> None:
        self.assertEqual(parse_edit_selection_data("EDITSEL|pick|2"), ("pick", 2))
        self.assertEqual(parse_edit_selection_data("EDITSEL|page|1"), ("page", 1))
        self.assertIsNone(parse_edit_selection_data("OTHER|pick|1"))


if __name__ == "__main__":
    unittest.main()
