"""Tests for the opposing-direction service and station crossovers."""
import unittest

from core.opposing_bot import OpposingBot
from core.track_network import TrackNetwork


class FakePath:
    total_length = 12000.0

    @staticmethod
    def grade_acceleration(distance):
        return 0.0


class FakeLine:
    path = FakePath()
    stations = [
        {"name": "A", "position": 1000.0},
        {"name": "B", "position": 3000.0},
        {"name": "C", "position": 5000.0},
        {"name": "D", "position": 7000.0},
    ]


class OpposingTrafficTests(unittest.TestCase):
    def test_opposing_train_moves_towards_lower_route_positions(self):
        bot = OpposingBot({"wagons": 4}, start_position=9000.0)
        bot.train.controller_notch = 4
        before = bot.train.position
        for _ in range(100):
            bot.update(0.1, FakeLine())
        self.assertLess(bot.train.position, before)
        self.assertEqual(bot.train.track_index, 0)

    def test_train_cannot_switch_onto_opposing_direction_lane(self):
        class FakeTrain:
            position = 800.0
            track_index = 1
            direction = 1
            track_change = None
            loco_length_m = 20.0
            consist_length_m = 150.0

            @property
            def occupied_track_indices(self):
                return {self.track_index}

        network = TrackNetwork(FakeLine(), {
            "lanes": [
                {"id": "opposing", "offset_m": -3.43, "direction": -1},
                {"id": "main", "offset_m": 0.0, "direction": 1},
                {"id": "spare", "offset_m": 3.43, "direction": 1},
            ],
            "first_switch_m": 900,
            "switch_spacing_m": 1500,
            "switch_length_m": 100,
            "switch_window_m": 120,
        })
        train = FakeTrain()
        self.assertFalse(network.request_lane_change(train, -1, [train]))
        self.assertTrue(network.request_lane_change(train, 1, [train]))

    def test_station_crossovers_are_added_outside_platforms(self):
        network = TrackNetwork(FakeLine(), {
            "first_switch_m": 11000,
            "switch_spacing_m": 15000,
            "switch_length_m": 100,
            "station_switches": True,
            "station_switch_interval": 2,
            "switch_offset_from_station_m": 260,
        })
        positions = [switch["position"] for switch in network.switches]
        self.assertIn(740.0, positions)
        self.assertIn(1260.0, positions)
        self.assertIn(4740.0, positions)
        self.assertIn(5260.0, positions)


if __name__ == "__main__":
    unittest.main()
