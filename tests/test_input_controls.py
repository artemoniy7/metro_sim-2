"""Regression tests for the revised cab controls."""
import unittest
from types import SimpleNamespace

import pygame

from systems.input import InputController


class InputControllerTests(unittest.TestCase):
    def setUp(self):
        self.controls = InputController()
        self.train = SimpleNamespace(
            controller_notch=0,
            speed=0.0,
            reverser_position=0,
            parking_brake_active=False,
            overspeed_emergency_active=False,
            overspeed_timer=2.0,
            manual_emergency_brake_active=False,
        )

    def press(self, key, mod=0):
        event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod)
        self.controls.handle_event(event, self.train)

    def test_w_and_s_move_controller_between_limits(self):
        for _ in range(6):
            self.press(pygame.K_w)
        self.assertEqual(self.train.controller_notch, 4)
        for _ in range(10):
            self.press(pygame.K_s)
        self.assertEqual(self.train.controller_notch, -3)

    def test_w_increases_controller_even_while_reverser_is_neutral(self):
        self.train.reverser_position = 0
        self.press(pygame.K_w)
        self.assertEqual(self.train.controller_notch, 1)

    def test_p_and_o_step_through_three_reverser_positions(self):
        self.press(pygame.K_p)
        self.assertEqual(self.train.reverser_position, 1)
        self.press(pygame.K_p)
        self.assertEqual(self.train.reverser_position, 1)
        self.press(pygame.K_o)
        self.assertEqual(self.train.reverser_position, 0)
        self.press(pygame.K_o)
        self.assertEqual(self.train.reverser_position, -1)

    def test_reverser_cannot_be_changed_while_moving(self):
        self.train.speed = 1.0
        self.press(pygame.K_p)
        self.assertEqual(self.train.reverser_position, 0)

    def test_reverser_stays_within_three_positions(self):
        for _ in range(5):
            self.press(pygame.K_p)
        self.assertEqual(self.train.reverser_position, 1)
        for _ in range(5):
            self.press(pygame.K_o)
        self.assertEqual(self.train.reverser_position, -1)

    def test_parking_brake_is_preserved_on_k(self):
        self.press(pygame.K_k)
        self.assertTrue(self.train.parking_brake_active)


if __name__ == "__main__":
    unittest.main()
