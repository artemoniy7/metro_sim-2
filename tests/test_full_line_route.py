"""Regression tests for full-line route selection and destination handling."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame

from systems.menu import MainMenu
from core.game import Game
from main import create_selected_game


class FullLineRouteTests(unittest.TestCase):
    def test_station_click_changes_only_the_start_station(self):
        menu = MainMenu.__new__(MainMenu)
        stations = [{"name": f"Station {i}", "position": i * 100.0} for i in range(5)]
        menu.available_lines = [({}, None, {"stations": stations})]
        menu.line_index = 0
        menu.start_index = 0
        menu.train_index = 0
        menu.buttons = {"station_3": pygame.Rect(0, 0, 20, 20)}

        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(5, 5)
        )
        menu.handle_event(event)

        self.assertEqual(menu.start_index, 3)
        self.assertFalse(hasattr(menu, "end_index"))

    def test_selected_game_does_not_pass_a_destination_position(self):
        menu = SimpleNamespace(
            selected_line=({"id": "line_x"}, SimpleNamespace(name="line_x.json"), {}),
            selected_train=(SimpleNamespace(name="train.json"), {}),
            selected_start_position=125.0,
        )
        with patch("core.game.Game") as game_class:
            create_selected_game(menu)

        game_class.assert_called_once_with(
            line_file="line_x.json",
            train_file="train.json",
            start_position=125.0,
        )

    def test_game_does_not_stop_at_an_old_destination_position(self):
        game = Game.__new__(Game)
        game.elapsed = 0.0
        game.controls = SimpleNamespace(update=Mock())
        game.doors_open = False
        game.bot_dispatch_timer = 0.0
        game.bots_enabled = False
        game.bot_trains = []
        game.opposing_trains = []
        game.train = SimpleNamespace(
            position=100.0,
            speed=12.0,
            controller_notch=2,
            doors_open=False,
            update=Mock(),
        )
        game.train.update.side_effect = lambda dt, line: setattr(
            game.train, "position", game.train.position + 5.0
        )
        game.line = SimpleNamespace(
            traffic_trains=[],
            path=SimpleNamespace(total_length=1000.0),
            opposing_signals=[],
            update_signals=Mock(),
        )
        game.track_network = SimpleNamespace(update_train=Mock())
        game.end_position = 100.0
        game.camera = SimpleNamespace(follow=Mock())
        game.audio = SimpleNamespace(update=Mock())
        game.station_simulation = SimpleNamespace(update=Mock())
        game._is_train_in_tunnel = Mock(return_value=False)

        game.update(0.1)

        self.assertEqual(game.train.position, 105.0)
        self.assertEqual(game.train.controller_notch, 2)


if __name__ == "__main__":
    unittest.main()
