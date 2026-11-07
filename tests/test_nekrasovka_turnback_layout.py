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
                self.assertIn(route_id, [route["id"] for route in options])

    def test_exit_direction_second_main_has_two_turnback_choices(self):
        routes = self.junctions.matching_routes(4.0, -1)
        options = self.junctions.available_routes(routes, 368.5, -1, 120.0)
        self.assertEqual(
            [route["id"] for route in options],
            ["LOCAL-OPPOSING-MAIN-INNER-1",
             "LOCAL-OPPOSING-MAIN-INNER-2"],
        )

    def _assert_two_options(self, offset, direction, position, expected_ids):
        routes = self.junctions.matching_routes(offset, direction)
        options = self.junctions.available_routes(routes, position, direction, 120.0)
        self.assertEqual([route["id"] for route in options], expected_ids)
        self.assertEqual(len(options), 2)

    def test_upper_crossover_is_switchable_in_both_directions(self):
        for offset, track_no in ((2.6666667, "1"), (1.3333333, "2")):
            other = "2" if track_no == "1" else "1"
            for direction, position, suffix in (
                (1, 268.5, "FWD"),
                (-1, 318.5, "REV"),
            ):
                with self.subTest(track=track_no, direction=direction):
                    self._assert_two_options(
                        offset, direction, position,
                        [
                            f"LOCAL-UPPER-INNER-{track_no}-STRAIGHT-{suffix}",
                            f"LOCAL-UPPER-INNER-{track_no}-INNER-{other}-{suffix}",
                        ],
                    )

    def test_lower_crossover_is_switchable_from_both_tracks_and_directions(self):
        # Toward increasing coordinates, the choice is stay on this track or cross.
        for offset, track_no in ((2.6666667, "1"), (1.3333333, "2")):
            other = "2" if track_no == "1" else "1"
            with self.subTest(track=track_no, direction=1):
                self._assert_two_options(
                    offset, 1, 18.5,
                    [
                        f"LOCAL-LOWER-INNER-{track_no}-STRAIGHT-FWD",
                        f"LOCAL-LOWER-INNER-{track_no}-INNER-{other}-FWD",
                    ],
                )
        # Toward decreasing coordinates, the two choices are the main line or crossover.
        for offset, track_no in ((2.6666667, "1"), (1.3333333, "2")):
            other = "2" if track_no == "1" else "1"
            main_id = f"LOCAL-INNER-{track_no}-MAIN-OTHER-SIDE"
            cross_id = f"LOCAL-LOWER-INNER-{track_no}-INNER-{other}-REV"
            with self.subTest(track=track_no, direction=-1):
                self._assert_two_options(offset, -1, 68.5, [main_id, cross_id])

    def test_only_two_crossover_locations_and_no_geometry_outside_sidings(self):
        segments = {segment["id"]: segment for segment in self.layout["track_segments"]}
        lower = (segments["inner_track_1"]["start_m"], 68.5)
        upper = (268.5, segments["inner_track_1"]["end_m"])
        crossover_routes = [
            route for route in self.layout["switches"]
            if "-INNER-" in route["id"] and "STRAIGHT" not in route["id"]
            and route["id"].startswith(("LOCAL-UPPER-", "LOCAL-LOWER-"))
        ]
        self.assertEqual(
            {(min(route["draw_start_m"], route["draw_end_m"]),
              max(route["draw_start_m"], route["draw_end_m"]))
             for route in crossover_routes},
            {lower, upper},
        )
        for route in crossover_routes:
            with self.subTest(route=route["id"]):
                self.assertGreaterEqual(
                    min(route["draw_start_m"], route["draw_end_m"]), 18.5
                )
                self.assertLessEqual(
                    max(route["draw_start_m"], route["draw_end_m"]), 318.5
                )
                self.assertNotEqual(route["from_offset_m"], route["to_offset_m"])

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
