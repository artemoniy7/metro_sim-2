"""Entry/exit lifecycle tests for local multi-route junctions."""
import unittest
from core.track_network import TrackNetwork

class FakePath:
    total_length = 2000.0

class FakeLine:
    path = FakePath()
    stations = []

class FakeTrain:
    def __init__(self, position=0.0, direction=-1, length=150.0):
        self.position = float(position)
        self.direction = direction
        self.track_index = 1
        self.loco_length_m = 20.0
        self.consist_length_m = length
        self.track_change = None

class JunctionRoutingTests(unittest.TestCase):
    def setUp(self):
        routes = [
            {"id": "branch-a", "junction_id": "j1", "position_m": 100, "start_m": 100, "end_m": 50, "from_offset_m": 0, "to_offset_m": 2, "travel_direction": -1, "route_order": 0},
            {"id": "branch-b", "junction_id": "j1", "position_m": 100, "start_m": 100, "end_m": 50, "from_offset_m": 0, "to_offset_m": 4, "travel_direction": -1, "route_order": 1},
        ]
        self.network = TrackNetwork(FakeLine(), {}, {"switches": routes})

    def test_options_cycle_before_entry(self):
        train = FakeTrain(250)
        self.assertTrue(self.network.request_route_selection(train, 1))
        self.assertEqual(train._junction_route_selection["j1"]["id"], "branch-b")
        self.assertTrue(self.network.request_route_selection(train, 1))
        self.assertEqual(train._junction_route_selection["j1"]["id"], "branch-a")

    def test_route_locks_when_leading_end_crosses_entry(self):
        train = FakeTrain(250)
        self.network.request_route_selection(train, 1)
        self.network.update_train(train)
        train.position = 70
        self.network.update_train(train)
        self.assertEqual(train._junction_active_zones[0]["route_id"], "branch-b")
        self.assertFalse(self.network.request_route_selection(train, 1))

    def test_zone_releases_after_tail_crosses_exit(self):
        train = FakeTrain(250, length=150)
        self.network.request_route_selection(train, 1)
        self.network.update_train(train)
        train.position = 70
        self.network.update_train(train)
        train.position = 40
        self.network.update_train(train)
        self.assertTrue(train._junction_active_zones)
        train.position = -120
        self.network.update_train(train)
        self.assertFalse(train._junction_active_zones)
        self.assertIsNone(train.track_change)
        self.assertAlmostEqual(train.track_offset_override_m, 4.0)

    def test_large_step_does_not_leave_zone_locked(self):
        train = FakeTrain(250, length=40)
        self.network.update_train(train)
        train.position = -10
        self.network.update_train(train)
        self.assertFalse(train._junction_active_zones)

if __name__ == "__main__":
    unittest.main()
