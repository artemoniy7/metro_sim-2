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

    def test_settings_open_controls_and_rebind_key(self):
        self.menu._save_settings = lambda: None
        self.menu.page = "settings"
        self.click("controls")
        self.menu.render(self.surface)
        self.click("bind_traction_up")
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t, mod=0)
        self.menu.handle_event(event)
        self.assertEqual(self.menu.keybinds["traction_up"], "t")
        self.assertIsNone(self.menu.capture_action)

    def test_duplicate_key_binding_is_rejected(self):
        self.menu._save_settings = lambda: None
        self.menu.page = "controls"
        self.menu.render(self.surface)
        self.click("bind_traction_up")
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, mod=0)
        self.menu.handle_event(event)
        self.assertEqual(self.menu.keybinds["traction_up"], "w")
        self.assertIn("уже назначена", self.menu.notice)

    def test_audio_group_volume_updates_audio_system(self):
        class FakeAudio:
            def __init__(self):
                self.values = {}
            def set_volume_group(self, group, value):
                self.values[group] = value

        fake = FakeAudio()
        self.menu._save_settings = lambda: None
        self.menu.page = "audio"
        self.menu.set_audio(fake)
        self.click("volume_train_down")
        self.assertEqual(self.menu.volume_groups["train"], 90)
        self.assertEqual(fake.values["train"], 0.9)

    def test_fullscreen_setting_is_not_present(self):
        self.menu.page = "settings"
        self.menu.render(self.surface)
        self.assertNotIn("fullscreen", self.menu.buttons)


if __name__ == "__main__":
    unittest.main()
