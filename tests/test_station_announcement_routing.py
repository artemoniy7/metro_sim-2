"""Tests for the manual, direction-aware station announcement sequence."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from systems.audio import AudioSystem


class StationAnnouncementSequenceTests(unittest.TestCase):
    def setUp(self):
        self.audio = AudioSystem.__new__(AudioSystem)
        self.audio.play_station_announcement = Mock(return_value=True)
        self.audio.station_announcement_cursor = None
        self.audio.station_announcement_station_count = 8

    def test_first_press_from_nekrasovka_announces_station_two(self):
        train = SimpleNamespace(direction=1)

        self.assertTrue(self.audio.toggle_station_announcer(train))

        self.audio.play_station_announcement.assert_called_once_with(2, "next", 1.0)

    def test_station_eight_uses_current_clip(self):
        train = SimpleNamespace(direction=1)
        for _ in range(6):
            self.audio.toggle_station_announcer(train)

        self.audio.play_station_announcement.reset_mock()
        self.assertTrue(self.audio.toggle_station_announcer(train))

        self.audio.play_station_announcement.assert_called_once_with(8, "current", 1.0)

    def test_after_reversal_next_press_announces_station_seven(self):
        train = SimpleNamespace(direction=1)
        for _ in range(7):
            self.audio.toggle_station_announcer(train)

        train.direction = -1
        self.audio.play_station_announcement.reset_mock()
        self.assertTrue(self.audio.toggle_station_announcer(train))

        self.audio.play_station_announcement.assert_called_once_with(7, "next", 1.0)

    def test_reverse_sequence_reaches_station_one_with_next_clip(self):
        train = SimpleNamespace(direction=1)
        for _ in range(7):
            self.audio.toggle_station_announcer(train)

        train.direction = -1
        for _ in range(6):
            self.audio.toggle_station_announcer(train)

        self.audio.play_station_announcement.reset_mock()
        self.assertTrue(self.audio.toggle_station_announcer(train))

        self.audio.play_station_announcement.assert_called_once_with(1, "next", 1.0)

    def test_reversing_again_advances_from_station_one_to_station_two(self):
        train = SimpleNamespace(direction=1)
        for _ in range(7):
            self.audio.toggle_station_announcer(train)
        train.direction = -1
        for _ in range(7):
            self.audio.toggle_station_announcer(train)

        train.direction = 1
        self.audio.play_station_announcement.reset_mock()
        self.assertTrue(self.audio.toggle_station_announcer(train))

        self.audio.play_station_announcement.assert_called_once_with(2, "next", 1.0)

    def test_sequence_does_not_require_train_position_or_line(self):
        train = SimpleNamespace(direction=1)

        self.assertTrue(self.audio.toggle_station_announcer(train, line=None))

        self.audio.play_station_announcement.assert_called_once_with(2, "next", 1.0)


if __name__ == "__main__":
    unittest.main()
