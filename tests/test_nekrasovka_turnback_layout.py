"""Geometry and route availability for both ends of the Nekrasovka turnback tracks."""
import json
import unittest
from pathlib import Path

from core.track_junctions import TrackJunctionSystem


class NekrasovkaTurnbackLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layout_path = (Path(__file__).resolve().parents[1]
                       / "data" / "track_layouts" / "line_15.json")
        cls.layout = json.loads(layout_path.read_text(encoding="utf-8"))
        cls.junctions = TrackJunctionSystem(cls.layout["switches"])

    def test_other_side_has_two_main_to_siding_choices(self):
        routes = self.junctions.matching_routes(0.0, 1)
        options = self.junctions.available_routes(routes, 0.0, 1, 120.0)
        self.assertEqual(
            [route["id"] for route in options],
            ["LOCAL-MAIN-INNER-1-OTHER-SIDE",
             "LOCAL-MAIN-INNER-2-OTHER-SIDE"],
        )

    def test_both_sidings_can_return_to_main_from_other_side(self):
        for offset, route_id in (
            (2.6666667, "LOCAL-INNER-1-MAIN-OTHER-SIDE"),
            (1.3333333, "LOCAL-INNER-2-MAIN-OTHER-SIDE"),
        ):
            with self.subTest(offset=offset):
                routes = self.junctions.matching_routes(offset, -1)
                options = self.junctions.available_routes(routes, 68.5, -1, 120.0)
                self.assertEqual([route["id"] for route in options], [route_id])


    def test_exit_direction_second_main_has_two_turnback_choices(self):
        routes = self.junctions.matching_routes(4.0, -1)
        options = self.junctions.available_routes(routes, 368.5, -1, 120.0)
        self.assertEqual(
            [route["id"] for route in options],
            ["LOCAL-OPPOSING-MAIN-INNER-1",
             "LOCAL-OPPOSING-MAIN-INNER-2"],
        )


    def test_each_siding_can_return_to_main_or_switch_to_the_other_siding(self):
        expected = (
            (2.6666667, [
                "LOCAL-INNER-1-MAIN",
                "LOCAL-INNER-1-INNER-2",
            ]),
            (1.3333333, [
                "LOCAL-INNER-2-MAIN",
                "LOCAL-INNER-2-INNER-1",
            ]),
        )
        for offset, expected_ids in expected:
            with self.subTest(offset=offset):
                routes = self.junctions.matching_routes(offset, 1)
                options = self.junctions.available_routes(routes, 318.5, 1, 120.0)
                self.assertEqual([route["id"] for route in options], expected_ids)

    def test_crossover_options_can_be_selected_without_losing_main_exit(self):
        for offset, crossover_id, main_id in (
            (2.6666667, "LOCAL-INNER-1-INNER-2", "LOCAL-INNER-1-MAIN"),
            (1.3333333, "LOCAL-INNER-2-INNER-1", "LOCAL-INNER-2-MAIN"),
        ):
            with self.subTest(offset=offset):
                routes = self.junctions.matching_routes(offset, 1)
                options = self.junctions.available_routes(routes, 318.5, 1, 120.0)
                self.assertEqual(len(options), 2)
                self.assertEqual(options[0]["id"], main_id)
                self.assertEqual(options[1]["id"], crossover_id)

    def test_existing_turnback_track_geometry_is_unchanged(self):
        segments = {segment["id"]: segment for segment in self.layout["track_segments"]}
        for segment_id in ("inner_track_1", "inner_track_2"):
            with self.subTest(segment=segment_id):
                self.assertEqual(
                    (segments[segment_id]["start_m"], segments[segment_id]["end_m"]),
                    (18.5, 318.5),
                )


if __name__ == "__main__":
    unittest.main()
