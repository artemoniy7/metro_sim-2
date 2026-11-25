"""Tests for transparent far-side door rendering on train sprites."""
import unittest
from types import SimpleNamespace

import pygame

from systems.renderer import Renderer


class RearSideDoorRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def make_renderer(self):
        renderer = Renderer.__new__(Renderer)
        renderer.door_animation_supported = True
        renderer.train_render_profile = SimpleNamespace()
        renderer.door_open_amount = 0.0
        renderer.door_left_image = pygame.Surface((91, 225), pygame.SRCALPHA)
        renderer.door_left_image.fill((255, 0, 0, 255))
        renderer.door_right_image = pygame.Surface((90, 225), pygame.SRCALPHA)
        renderer.door_right_image.fill((0, 255, 0, 255))
        return renderer

    def test_door_apertures_become_transparent_without_erasing_body(self):
        renderer = self.make_renderer()
        source = pygame.Surface((2164, 340), pygame.SRCALPHA)
        sprite = pygame.Surface((2164, 340), pygame.SRCALPHA)
        sprite.fill((80, 120, 160, 255))

        renderer._clear_door_openings(sprite, source, 2164, 340, is_loco=False)

        self.assertEqual(sprite.get_at((250, 180)).a, 0)
        self.assertEqual(sprite.get_at((500, 180)).a, 255)

    def test_far_side_doors_are_visible_through_the_transparent_aperture(self):
        renderer = self.make_renderer()
        source = pygame.Surface((2164, 340), pygame.SRCALPHA)
        sprite = pygame.Surface((2164, 340), pygame.SRCALPHA)
        sprite.fill((80, 120, 160, 255))
        background = pygame.Surface((2164, 340), pygame.SRCALPHA)
        background.fill((15, 20, 25, 255))

        renderer._draw_rear_doors(
            background, source, 0, 0, 2164, 340, is_loco=False
        )
        renderer._clear_door_openings(
            sprite, source, 2164, 340, is_loco=False
        )
        background.blit(sprite, (0, 0))

        # First door opening shows the tinted far-side left door leaf.
        pixel = background.get_at((180, 80))
        self.assertGreater(pixel.r, pixel.g)
        self.assertGreater(pixel.r, 100)

    def test_far_side_doors_follow_the_opening_animation(self):
        renderer = self.make_renderer()
        source = pygame.Surface((2164, 340), pygame.SRCALPHA)
        closed = pygame.Surface((2164, 340), pygame.SRCALPHA)
        opened = pygame.Surface((2164, 340), pygame.SRCALPHA)
        closed.fill((0, 0, 0, 0))
        opened.fill((0, 0, 0, 0))

        renderer.door_open_amount = 0.0
        renderer._draw_rear_doors(
            closed, source, 0, 0, 2164, 340, is_loco=False
        )
        renderer.door_open_amount = 1.0
        renderer._draw_rear_doors(
            opened, source, 0, 0, 2164, 340, is_loco=False
        )

        self.assertNotEqual(closed.get_at((180, 80)), opened.get_at((180, 80)))


if __name__ == "__main__":
    unittest.main()
