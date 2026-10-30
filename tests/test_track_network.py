"""Unit tests for parallel-track switching and switch occupancy."""
import unittest

from core.track_network import TrackNetwork


class FakePath:
    total_length = 12000.0


class FakeLine:
    path = FakePath()


class FakeTrain:
    def __init__(self, position, track_index=1, length=150.0):
        self.position = float(position)
        self.track_index = track_index
        self.track_change = None
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

    def test_change_requires_a_nearby_switch(self):
        train = FakeTrain(100)
        self.assertFalse(self.network.request_lane_change(train, -1, [train]))

    def test_change_starts_at_switch_and_occupies_both_tracks(self):
        train = FakeTrain(900)
        self.assertTrue(self.network.request_lane_change(train, -1, [train]))
        self.assertEqual(train.occupied_track_indices, {0, 1})
        self.assertNotEqual(self.network.lane_offset(train, 900),
                            self.network.lane_offset_for_index(1))

    def test_switch_is_blocked_by_train_on_conflicting_track(self):
        train = FakeTrain(900)
        other = FakeTrain(820, track_index=0)
        self.assertFalse(self.network.request_lane_change(train, -1, [train, other]))

    def test_switch_is_released_only_after_tail_clears(self):
        train = FakeTrain(900)
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


if __name__ == "__main__":
    unittest.main()
