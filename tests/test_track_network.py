"""Unit tests for parallel tracks, local sidings and bidirectional switches."""
import unittest

from core.track_network import TrackNetwork


class FakePath:
    total_length = 12000.0


class FakeLine:
    path = FakePath()
    stations = []


class FakeTrain:
    def __init__(self, position, track_index=1, length=150.0, direction=1):
        self.position = float(position)
        self.track_index = track_index
        self.track_change = None
        self.direction = direction
        self.loco_length_m = 20.0
        self.consist_length_m = length

    @property
    def occupied_track_indices(self):
        if self.track_change:
            return {self.track_change["from"], self.track_change["to"]}
        return {self.track_index}


class TrackNetworkTests(unittest.TestCase):
    def setUp(self):
        self.network = TrackNetwork(FakeLine(), {
            "first_switch_m": 900,
            "switch_spacing_m": 1500,
            "switch_length_m": 100,
            "switch_window_m": 120,
        })

    def test_lane_spacing_is_measured_in_world_metres(self):
        self.assertEqual(len(self.network.lanes), 2)
        self.assertAlmostEqual(self.network.lane_offset_for_index(0), -3.43)
        self.assertAlmostEqual(self.network.lane_offset_for_index(1), 0.0)

    def test_change_requires_a_nearby_switch(self):
        train = FakeTrain(100)
        self.assertFalse(self.network.request_lane_change(train, -1, [train]))

    def test_change_starts_at_switch_and_occupies_both_tracks(self):
        train = FakeTrain(800)
        self.assertTrue(self.network.request_lane_change(train, -1, [train]))
        self.assertEqual(train.occupied_track_indices, {0, 1})
        self.assertNotEqual(self.network.lane_offset(train, 875),
                            self.network.lane_offset_for_index(1))

    def test_switch_is_blocked_by_train_on_conflicting_track(self):
        train = FakeTrain(800)
        other = FakeTrain(800, track_index=0)
        self.assertFalse(self.network.request_lane_change(train, -1, [train, other]))

    def test_switch_is_released_only_after_tail_clears(self):
        train = FakeTrain(800)
        self.assertTrue(self.network.request_lane_change(train, -1, [train]))
        change_end = train.track_change["end"]
        train.position = change_end + 100
        self.network.update_train(train)
        self.assertEqual(train.track_index, 1)
        self.assertIsNotNone(train.track_change)
        train.position = change_end + train.consist_length_m + 1
        self.network.update_train(train)
        self.assertEqual(train.track_index, 0)
        self.assertIsNone(train.track_change)

    def test_local_bidirectional_siding_switches_are_configurable(self):
        network = TrackNetwork(FakeLine(), {
            "main_lane": 3,
            "switch_length_m": 40,
            "switch_window_m": 120,
            "lanes": [
                {"id": "outer_a", "offset_m": -6, "direction": -1},
                {"id": "siding_a", "offset_m": -2, "direction": 0, "start_m": 20, "end_m": 270},
                {"id": "siding_b", "offset_m": 2, "direction": 0, "start_m": 20, "end_m": 270},
                {"id": "outer_b", "offset_m": 6, "direction": 1},
            ],
            "switches": [
                {"id": "A", "position": 40, "lane_pairs": [[0, 1], [1, 2], [2, 3]]},
                {"id": "B", "position": 250, "lane_pairs": [[0, 1], [1, 2], [2, 3]]},
            ],
        })
        self.assertEqual(len(network.lanes), 4)
        self.assertEqual(len(network.switches), 2)
        self.assertAlmostEqual(network.switches[1]["position"] - network.switches[0]["position"],
                               network.switch_length + 170)
        train = FakeTrain(370, track_index=3, direction=-1)
        self.assertTrue(network.request_lane_change(train, -1, [train], target_lane=1))
        self.assertEqual(train.track_change["to"], 1)

    def test_reverse_train_can_take_bidirectional_switch(self):
        network = TrackNetwork(FakeLine(), {
            "main_lane": 1,
            "switch_length_m": 40,
            "switch_window_m": 120,
            "lanes": [
                {"id": "siding", "offset_m": -2, "direction": 0},
                {"id": "main", "offset_m": 0, "direction": 1},
            ],
            "switches": [{"id": "REV", "position": 800, "lane_pairs": [[0, 1]]}],
        })
        train = FakeTrain(900, track_index=1, direction=-1)
        self.assertTrue(network.request_lane_change(train, -1, [train]))
        self.assertEqual(train.track_change["direction"], -1)
        self.assertAlmostEqual(network.lane_offset(train, 880),
                               network.lane_offset_for_index(1))
        self.assertAlmostEqual(network.lane_offset(train, 780),
                               network.lane_offset_for_index(0))


if __name__ == "__main__":
    unittest.main()
