#!/usr/bin/env python3
"""最小 smoke tests：验证脚本、数据加载和单名/双名流程。"""

import unittest
import tempfile
from pathlib import Path

import naming
import search_classics


class NamingSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        naming.load_characters()
        naming.load_sensitive()
        naming.load_poetry_names()

    def test_solar_lunar_conversion(self):
        self.assertEqual(naming.solar_to_lunar(2024, 2, 10), (2024, 1, 1, False))
        self.assertEqual(naming.lunar_to_solar(2024, 1, 1), naming.date(2024, 2, 10))

    def test_leap_lunar_month(self):
        self.assertEqual(naming.solar_to_lunar(2023, 3, 22), (2023, 2, 1, True))
        self.assertEqual(naming.lunar_to_solar(2023, 2, 1, True), naming.date(2023, 3, 22))

    def test_zi_hour(self):
        self.assertTrue(naming.hour_ganzhi("甲", 23).endswith("子"))

    def test_solar_term_boundary(self):
        self.assertNotEqual(
            naming.month_ganzhi(2024, 3, 5),
            naming.month_ganzhi(2024, 3, 6),
        )

    def test_full_name_pronunciation(self):
        result = naming.yinyun("田安")
        self.assertIn("声调2、1", result)
        self.assertNotEqual(result, naming.yinyun("安"))

    def test_birth_parser_keeps_minute_validation(self):
        self.assertEqual(naming.parse_birth("1996-03-21 08:30")[4], 30)
        with self.assertRaises(ValueError):
            naming.parse_birth("1996-02-30")

    def test_simplified_traditional_classics_search(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "0.詩詞" / "詩經.txt"
            path.parent.mkdir(parents=True)
            path.write_text("有美一人，清揚婉兮。\n", encoding="utf-8")
            matches = search_classics.search(directory, "清扬", "诗经", limit=3)
            self.assertEqual(len(matches), 1)
            self.assertIn("清揚", matches[0]["text"])

    def test_sensitive_filter(self):
        self.assertIsNotNone(naming.sensitive_match("杜子腾"))
        self.assertIsNone(naming.sensitive_match("田安"))

    def test_poetry_source_match(self):
        result = naming.poetry_match("安")
        self.assertEqual(result["source"], "《道德经》第八十章")
        self.assertIsNotNone(naming.poetry_match("子衿"))

    def test_classics_root_can_enrich_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "诗经.txt"
            path.write_text("高山仰止，景行行止。\n", encoding="utf-8")
            records = naming.load_classics(directory)
            result = naming.poetry_match("高山", records)
            self.assertEqual(result["source"], "诗经.txt:1")

    def test_single_name_without_hour(self):
        result = naming.run(
            1996, 3, 21, 0, "neutral", "田", "", "", "classical",
            count=5, name_length=1, hour_provided=False
        )
        self.assertEqual(len(result["candidates"]), 5)
        self.assertTrue(all(len(item["name"]) == 1 for item in result["candidates"]))
        self.assertIn("不可视为精确结论", result["ziwei_note"])
        self.assertTrue(result["hour_unknown"])
        self.assertIsNone(result["xiyongshen"])
        self.assertFalse(any(item["name"] in {"衣", "艳", "鹦", "呓"}
                             for item in result["candidates"]))

    def test_double_name_with_hour_and_json_fields(self):
        result = naming.run(
            1996, 3, 21, 8, "neutral", "田", "", "", "classical",
            count=5, name_length=2, hour_provided=True
        )
        self.assertEqual(len(result["candidates"]), 5)
        self.assertTrue(all(len(item["name"]) == 2 for item in result["candidates"]))
        self.assertIn("年柱", result["bazi"])
        self.assertIn("wuxing", result["candidates"][0])
        self.assertLessEqual(result["candidates"][0]["score"], 100)
        self.assertFalse(result["hour_unknown"])


if __name__ == "__main__":
    unittest.main()
