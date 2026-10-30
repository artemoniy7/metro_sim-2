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
