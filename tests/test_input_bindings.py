"""Tests for configurable keyboard bindings."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from systems.input import InputController


class FakeTrain:
    def __init__(self):
        self.controller_notch = 0
        self.speed = 0.0
        self.reverser_position = 0
        self.parking_brake_active = False
        self.overspeed_emergency_active = True
        self.overspeed_timer = 5.0


class InputBindingTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.controls = InputController()
        self.train = FakeTrain()

    def tearDown(self):
        pygame.quit()

    def test_remapped_traction_key_changes_notch(self):
        self.controls.set_keybinds({"traction_up": "t"})
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t, mod=0)
        self.controls.handle_event(event, self.train)
        self.assertEqual(self.train.controller_notch, 1)

    def test_shift_chord_is_distinct_from_plain_key(self):
        shift_a = pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_a, mod=pygame.KMOD_SHIFT
        )
        plain_a = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0)
        self.assertTrue(self.controls.matches(shift_a, "select_left_door"))
        self.assertFalse(self.controls.matches(plain_a, "select_left_door"))
        self.assertTrue(self.controls.matches(plain_a, "open_left_door"))

    def test_emergency_brake_releases_on_key_up(self):
        down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0)
        up = pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE, mod=0)
        self.controls.handle_event(down, self.train)
        self.assertTrue(self.controls.emergency)
        self.controls.handle_event(up, self.train)
        self.assertFalse(self.controls.emergency)


if __name__ == "__main__":
    unittest.main()
