"""Regression tests for train menu preview assets and station platform geometry."""

import json
import unittest
from pathlib import Path

from core.train_models.oka import profile as oka_profile
from core.train_models.moscow_2020 import profile as moscow_2020_profile


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


class MenuPreviewAndStationLayoutTests(unittest.TestCase):
    def test_menu_preview_sprite_files_match_model_profiles(self):
        for profile in (oka_profile, moscow_2020_profile):
            folder = ASSETS / "trains" / profile.ASSET_DIRECTORY
            for sprite_name in ("loco", "door_left", "door_right"):
                with self.subTest(model=profile.TRAIN_MODEL_ID, sprite=sprite_name):
                    self.assertTrue(
                        (folder / profile.SPRITE_FILES[sprite_name]).is_file()
                    )

    def test_yugo_vostochnaya_uses_side_platforms_and_centered_tracks(self):
        line_path = ROOT / "data" / "lines" / "line_15.json"
        line = json.loads(line_path.read_text(encoding="utf-8"))
        station = next(
            item for item in line["stations"]
            if item["name"] == "Юго-Восточная"
        )
        self.assertEqual(station["platform_type"], "side")
        self.assertEqual(station["platform_layout"], "side")
        self.assertAlmostEqual(station["track_center_offset_m"], 1.7)
        self.assertEqual(station["track_center_transition_m"], 100)


if __name__ == "__main__":
    unittest.main()
