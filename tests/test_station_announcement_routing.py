"""Tests for direction-aware station announcements."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from systems.audio import AudioSystem


class StationAnnouncementRoutingTests(unittest.TestCase):
    def setUp(self):
        self.audio = AudioSystem.__new__(AudioSystem)
        self.audio.play_station_announcement = Mock(return_value=True)
        self.audio._last_terminal_arrival = None
        self.line = SimpleNamespace(stations=[
            {"name": "Некрасовка", "position": 500.0, "length_m": 163.0},
            {"name": "Лухмановская", "position": 2387.7, "length_m": 163.0},
            {"name": "Улица Дмитриевского", "position": 3727.22, "length_m": 163.0},
            {"name": "Косино", "position": 5825.04, "length_m": 163.0},
            {"name": "Юго-Восточная", "position": 7947.38, "length_m": 163.0},
            {"name": "Окская", "position": 10742.35, "length_m": 163.0},
            {"name": "Стахановская", "position": 12817.43, "length_m": 163.0},
            {"name": "Нижегородская", "position": 14365.04, "length_m": 163.0},
        ])

    def test_departure_from_nekrasovka_announces_station_two(self):
        train = SimpleNamespace(position=500.0, direction=1, speed=0.0)

        self.assertTrue(self.audio.announce_departure(train, self.line))

        self.audio.play_station_announcement.assert_called_once_with(2, "next", 1.0)

    def test_departure_after_terminal_reversal_announces_station_seven(self):
        train = SimpleNamespace(position=14365.04, direction=-1, speed=0.0)

        self.assertTrue(self.audio.announce_departure(train, self.line))

        self.audio.play_station_announcement.assert_called_once_with(7, "next", 1.0)

    def test_terminal_arrival_announces_current_station_only_once(self):
        train = SimpleNamespace(position=14365.04, direction=1, speed=0.0)

        self.assertTrue(self.audio.announce_terminal_arrival(train, self.line))
        self.assertFalse(self.audio.announce_terminal_arrival(train, self.line))

        self.audio.play_station_announcement.assert_called_once_with(8, "current", 1.0)

    def test_arrival_at_nekrasovka_from_reverse_direction_announces_station_one(self):
        train = SimpleNamespace(position=500.0, direction=-1, speed=0.0)

        self.assertTrue(self.audio.announce_terminal_arrival(train, self.line))

        self.audio.play_station_announcement.assert_called_once_with(1, "current", 1.0)

    def test_intermediate_station_does_not_play_terminal_current_clip(self):
        train = SimpleNamespace(position=3727.22, direction=1, speed=0.0)

        self.assertFalse(self.audio.announce_terminal_arrival(train, self.line))

        self.audio.play_station_announcement.assert_not_called()


if __name__ == "__main__":
    unittest.main()
