"""Tests for track geometry while interactive switching is disabled."""
import unittest

from core.track_network import TrackNetwork


class FakePath:
    total_length = 12000.0


class FakeLine:
    path = FakePath()
    stations = []


class FakeTrain:
    def __init__(self, position=800.0, track_index=1):
        self.position = float(position)
        self.track_index = track_index
        self.track_change = None
        self._junction_route_state = None
        self.direction = 1
        self.loco_length_m = 20.0
        self.consist_length_m = 150.0


class TrackNetworkTests(unittest.TestCase):
    def setUp(self):
        self.network = TrackNetwork(FakeLine(), {
            "first_switch_m": 900,
            "switch_spacing_m": 1500,
            "switch_length_m": 100,
            "switch_window_m": 120,
            "lanes": [
                {"id": "opposing", "label": "Встречный путь", "offset_m": -3.43},
                {"id": "main", "label": "Главный путь", "offset_m": 0.0},
            ],
        })

    def test_track_geometry_and_switch_positions_are_preserved(self):
        self.assertEqual(len(self.network.lanes), 2)
        self.assertAlmostEqual(self.network.lane_offset_for_index(0), -3.43)
        self.assertAlmostEqual(self.network.lane_offset_for_index(1), 0.0)
        self.assertTrue(self.network.switches)
        self.assertEqual(self.network.switches[0]["position"], 900)

    def test_local_track_segments_and_switch_metadata_are_preserved(self):
        layout = {
            "track_segments": [
                {"id": "siding", "start_m": 10, "end_m": 100, "offset_m": 2}
            ],
            "switches": [
                {"id": "junction-a", "start_m": 20, "end_m": 40,
                 "from_offset_m": 0, "to_offset_m": 2}
            ],
        }
        network = TrackNetwork(FakeLine(), {}, local_layout=layout)
        self.assertEqual(network.local_track_segments, layout["track_segments"])
        self.assertEqual(network.local_switches, layout["switches"])

    def test_user_request_cannot_change_track(self):
        train = FakeTrain()
        self.assertFalse(self.network.request_lane_change(train, -1, [train]))
        self.assertIsNone(train.track_change)
        self.assertEqual(train.track_index, 1)
        self.assertEqual(
            self.network.last_message,
            "Переключение путей временно отключено",
        )

    def test_update_does_not_apply_or_continue_legacy_transition(self):
        train = FakeTrain()
        train.track_change = {
            "from": 1, "to": 0, "start": 700, "end": 900,
        }
        train._junction_route_state = {"entry": 700, "exit": 900}
        self.network.update_train(train)
        self.assertIsNone(train.track_change)
        self.assertIsNone(train._junction_route_state)
        self.assertEqual(train.track_index, 1)


if __name__ == "__main__":
    unittest.main()
