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

    def test_circular_button_hitbox_rejects_square_corners(self):
        ui = DriverCabUI()
        rect = pygame.Rect(10, 10, 48, 48)

        self.assertTrue(ui._button_hit("close_doors", rect, rect.center))
        self.assertFalse(ui._button_hit("close_doors", rect, (10, 10)))

    def test_announcement_button_plays_selected_clip_then_advances(self):
        ui = DriverCabUI()
        first = {"station_number": 2, "kind": "next", "label": "Бибирево отпр."}
        second = {"station_number": 3, "kind": "current", "label": "Отрадное"}
        ui.announcement_items = [first, second]
        ui.buttons["play_announcement"] = pygame.Rect(20, 20, 56, 56)
        train = SimpleNamespace(controller_notch=0)

        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(48, 48)
        )
        action = ui.handle_event(event, train)

        self.assertEqual(action, {"play_announcement": first})
        self.assertEqual(ui.announcement_index, 1)

    def test_departure_announcement_plays_the_following_station_clip(self):
        ui = DriverCabUI()
        line = SimpleNamespace(stations=[
            {"name": "Станция А"},
            {"name": "Станция Б"},
            {"name": "Станция В"},
        ])
        audio = SimpleNamespace(station_announcement_sounds={
            1: {"current": object(), "next": object()},
            2: {"current": object(), "next": object()},
            3: {"current": object(), "next": object()},
        })
        game = SimpleNamespace(audio=audio)

        ui._build_announcement_items(line, game)

        departures = [item for item in ui.announcement_items if item["kind"] == "next"]
        self.assertEqual(
            departures,
            [
                {
                    "station_number": 2,
                    "display_station_number": 1,
                    "kind": "next",
                    "label": "Станция А — отпр.",
                },
                {
                    "station_number": 3,
                    "display_station_number": 2,
                    "kind": "next",
                    "label": "Станция Б — отпр.",
                },
            ],
        )

    def test_route_drawer_tabs_toggle_open_and_closed(self):
        ui = DriverCabUI()
        ui.buttons["tab_motion"] = pygame.Rect(10, 10, 48, 48)
        train = SimpleNamespace(controller_notch=0)

        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(34, 34)
        )
        ui.handle_event(event, train)
        self.assertEqual(ui.drawer, "motion")

        ui.buttons["tab_motion"] = pygame.Rect(10, 10, 48, 48)
        ui.handle_event(event, train)
        self.assertIsNone(ui.drawer)


if __name__ == "__main__":
    unittest.main()
