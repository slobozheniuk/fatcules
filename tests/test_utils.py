import math
from datetime import datetime, timedelta, timezone
import unittest

from fatcules.formatting import format_stats_summary, parse_float, parse_height_cm
from fatcules.stats import average_daily_drop, parse_series


class TestParsing(unittest.TestCase):
    def test_parse_float(self) -> None:
        self.assertEqual(parse_float(" 82.5 "), 82.5)
        self.assertEqual(parse_float("82,5"), 82.5)
        self.assertIsNone(parse_float("abc"))

    def test_parse_height_cm(self) -> None:
        self.assertEqual(parse_height_cm("180"), 180)
        self.assertEqual(parse_height_cm("170.5"), 170.5)
        self.assertEqual(parse_height_cm("249,99"), 249.99)
        self.assertIsNone(parse_height_cm("40"))
        self.assertIsNone(parse_height_cm("999"))
        self.assertIsNone(parse_height_cm("bad"))


class TestStats(unittest.TestCase):
    def test_average_drop(self) -> None:
        now = datetime.now(timezone.utc)
        series = [
            (now - timedelta(days=4), 22.0),
            (now - timedelta(days=2), 21.0),
            (now, 20.5),
        ]
        drop = average_daily_drop(series, 7)
        expected = (22.0 - 20.5) / 4  # kg per day
        self.assertTrue(math.isclose(drop or 0, expected, rel_tol=1e-6))

    def test_average_drop_not_enough(self) -> None:
        now = datetime.now(timezone.utc)
        series = [(now - timedelta(days=1), 20.0)]
        self.assertIsNone(average_daily_drop(series, 7))

    def test_parse_series(self) -> None:
        now = datetime.now(timezone.utc)
        iso = now.isoformat()
        parsed = parse_series([{"recorded_at": iso, "fat_weight_kg": 10.5}])
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0][1], 10.5)


class TestFormatting(unittest.TestCase):
    def test_format_stats_summary(self) -> None:
        summary = format_stats_summary(9.9, {7: -0.2, 14: None, 30: -0.1}, 24.6)
        self.assertIn("Current fat weight: 9.90 kg", summary)
        self.assertIn("7d: -0.200 kg/day", summary)
        self.assertIn("14d: not enough data", summary)
        self.assertIn("Latest BMI: 24.6", summary)


if __name__ == "__main__":
    unittest.main()
