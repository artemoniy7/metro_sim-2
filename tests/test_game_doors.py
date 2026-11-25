"""Regression tests for reliable door opening controls."""
import unittest
from types import SimpleNamespace

from core.game import Game


class DoorOpeningTests(unittest.TestCase):
    def make_game(self, speed=0.0, doors_available=True):
        game = Game.__new__(Game)
        game.train = SimpleNamespace(
            speed=speed,
            doors_open=False,
            pneumatics=SimpleNamespace(doors_available=doors_available),
        )
        game.doors_open = False
        game.selected_door_side = None
        played = []
        game.audio = SimpleNamespace(play_door_sound=lambda: played.append(True))
        game.played_door_sounds = played
        return game

    def test_open_command_selects_side_and_opens_without_separate_selection(self):
        game = self.make_game()

        self.assertTrue(game._open_selected_doors("left"))

        self.assertEqual(game.selected_door_side, "left")
        self.assertTrue(game.doors_open)
        self.assertTrue(game.train.doors_open)
        self.assertEqual(game.played_door_sounds, [True])

    def test_opening_other_side_updates_selection(self):
        game = self.make_game()
        game.selected_door_side = "left"

        self.assertTrue(game._open_selected_doors("right"))

        self.assertEqual(game.selected_door_side, "right")
        self.assertTrue(game.doors_open)

    def test_doors_remain_closed_while_train_is_moving(self):
        game = self.make_game(speed=0.06)

        self.assertFalse(game._open_selected_doors("left"))
        self.assertFalse(game.doors_open)
        self.assertFalse(game.train.doors_open)

    def test_low_door_pressure_blocks_opening(self):
        game = self.make_game(doors_available=False)

        self.assertFalse(game._open_selected_doors("right"))
        self.assertFalse(game.doors_open)
        self.assertEqual(game.selected_door_side, "right")


if __name__ == "__main__":
    unittest.main()
