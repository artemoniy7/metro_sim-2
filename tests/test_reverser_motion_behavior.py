"""Regression tests for neutral audio, reverse cab framing and station walls."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from core.camera import Camera
from systems.audio import AudioSystem
from systems.renderer import Renderer


class FakeChannel:
    def __init__(self):
        self.stopped = 0

    def stop(self):
        self.stopped += 1


class ReverserMotionBehaviorTests(unittest.TestCase):
    def test_neutral_reverser_suppresses_all_motion_sound_updates(self):
        audio = AudioSystem.__new__(AudioSystem)
        audio._stop_motion_sounds = Mock()
        audio._update_tunnel_curve = Mock()
        audio._update_rolling = Mock()
        audio._update_engine = Mock()
        train = SimpleNamespace(reverser_position=0, speed=0.0)

        audio._update_motion_sounds(train, 1.0, in_tunnel=True)

        audio._stop_motion_sounds.assert_called_once_with()
        audio._update_tunnel_curve.assert_not_called()
        audio._update_rolling.assert_not_called()
        audio._update_engine.assert_not_called()

    def test_stopping_motion_audio_stops_each_drive_channel(self):
        audio = AudioSystem.__new__(AudioSystem)
        channels = [FakeChannel() for _ in range(7)]
        audio.rolling_channels = channels[:2]
        audio.engine_channels = channels[2:5]
        audio._extra_engine_channels = [channels[5]]
        audio._tunnel_curve_channel = channels[6]
        audio._engine_volumes = [0.5, 0.4, 0.3]
        audio._tunnel_curve_volume = 0.4
        audio._chopper_was_active = True
        audio._high_component_was_active = True

        audio._stop_motion_sounds()

        self.assertTrue(all(channel.stopped == 1 for channel in channels))
        self.assertEqual(audio._engine_volumes, [0.0, 0.0, 0.0])
        self.assertEqual(audio._tunnel_curve_volume, 0.0)
        self.assertFalse(audio._chopper_was_active)
        self.assertFalse(audio._high_component_was_active)

    def test_camera_follows_second_cab_without_mirroring_the_world(self):
        train = SimpleNamespace(
            position=500.0,
            direction=-1,
            active_cab=1,
            loco_length_m=20.0,
            consist_length_m=153.0,
        )
        camera = Camera((1000, 700), zoom=2.0)
        camera.focus_screen_x = 320.0

        camera.follow(train, route_length=1000.0)

        second_cab_world_x = (
            1000.0 - train.position - train.loco_length_m
            + train.consist_length_m - train.loco_length_m
        )
        self.assertAlmostEqual(
            camera.x,
            second_cab_world_x - camera.focus_screen_x / camera.pixels_per_metre,
        )
        self.assertEqual(train.position, 500.0)
        self.assertFalse(hasattr(camera, "cab_swapped"))

    def test_parallel_track_offset_keeps_its_world_side_after_cab_change(self):
        renderer = Renderer.__new__(Renderer)
        renderer.main_lane_offset_m = 0.0

        offset = renderer._lane_offset_pixels({"offset_m": 4.0}, scale=2.0)

        self.assertEqual(offset, 8.0)

    def test_station_wall_uses_the_same_fixed_world_orientation(self):
        normal_top = Renderer._station_wall_top(200, 170, 5, False)
        second_cab_top = Renderer._station_wall_top(200, 170, 5, True)

        self.assertEqual(normal_top, 25)
        self.assertEqual(second_cab_top, normal_top)


if __name__ == "__main__":
    unittest.main()
