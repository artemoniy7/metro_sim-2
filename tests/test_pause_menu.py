"""Tests for the in-game pause menu."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from systems.pause_menu import PauseMenu


class PauseMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.menu = PauseMenu()
        self.surface = pygame.Surface((800, 600))

    def click(self, key):
        self.menu.render(self.surface)
        rect = self.menu.buttons[key]
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center
        )
        return self.menu.handle_event(event)

    def test_escape_from_pause_resumes_game(self):
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        self.assertEqual(self.menu.handle_event(event), "resume")

    def test_pause_menu_has_continue_settings_and_main_menu_actions(self):
        self.menu.render(self.surface)
        self.assertEqual(
            set(self.menu.buttons),
            {"continue", "settings", "main_menu"},
        )
        self.assertIsNone(self.click("settings"))
        self.assertEqual(self.menu.page, "settings")

    def test_settings_escape_returns_to_pause_menu(self):
        self.menu.page = "settings"
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        self.assertIsNone(self.menu.handle_event(event))
        self.assertEqual(self.menu.page, "pause")

    def test_main_menu_action_is_reported(self):
        self.assertEqual(self.click("main_menu"), "main_menu")


if __name__ == "__main__":
    unittest.main()
