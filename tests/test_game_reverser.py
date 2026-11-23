"""Tests for the cab reverser interlock."""
import unittest
from types import SimpleNamespace

from core.game import Game


class ReverserControlTests(unittest.TestCase):
    def make_game(self):
        game = Game.__new__(Game)
        game.train = SimpleNamespace(
            active_cab=0,
            reverser_position=0,
            direction=1,
            speed=0.0,
        )
        return game

    def test_reverser_changes_direction_when_stopped(self):
        game = self.make_game()

        self.assertTrue(game._set_reverser_position(-1))
        self.assertEqual(game.train.reverser_position, -1)
        self.assertEqual(game.train.direction, -1)

    def test_opposite_direction_is_interlocked_while_moving(self):
        game = self.make_game()
        game.train.speed = 4.0

        self.assertFalse(game._set_reverser_position(-1))
        self.assertEqual(game.train.reverser_position, 0)
        self.assertEqual(game.train.direction, 1)

    def test_neutral_and_current_direction_are_available_while_moving(self):
        game = self.make_game()
        game.train.speed = 4.0

        self.assertTrue(game._set_reverser_position(0))
        self.assertTrue(game._set_reverser_position(1))
        self.assertEqual(game.train.reverser_position, 1)
        self.assertEqual(game.train.direction, 1)


if __name__ == "__main__":
    unittest.main()
