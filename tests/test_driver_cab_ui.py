"""Tests for the interactive driver cab overlay."""
import unittest
from types import SimpleNamespace

import pygame

from systems.driver_cab_ui import DriverCabUI


class DriverCabUITests(unittest.TestCase):
    def test_vertical_lever_maps_top_to_maximum_traction_and_bottom_to_brake(self):
        ui = DriverCabUI()
        ui.buttons["lever_track"] = pygame.Rect(40, 100, 12, 180)
        train = SimpleNamespace(controller_notch=0)

        ui._set_notch_from_y(100, train)
        self.assertEqual(train.controller_notch, 4)

        ui._set_notch_from_y(280, train)
        self.assertEqual(train.controller_notch, -3)

    def test_route_drawer_tabs_toggle_open_and_closed(self):
        ui = DriverCabUI()
        ui.buttons["tab_motion"] = pygame.Rect(10, 10, 100, 40)
        train = SimpleNamespace(controller_notch=0)

        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(20, 20)
        )
        ui.handle_event(event, train)
        self.assertEqual(ui.drawer, "motion")

        ui.buttons["tab_motion"] = pygame.Rect(10, 10, 100, 40)
        ui.handle_event(event, train)
        self.assertIsNone(ui.drawer)


if __name__ == "__main__":
    unittest.main()
