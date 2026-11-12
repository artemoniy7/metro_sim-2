"""Focused tests for 81-777 wheel squeal and brake-loop playback."""

import unittest
from types import SimpleNamespace

from systems.audio import AudioSystem


class FakeChannel:
    def __init__(self):
        self.busy = False
        self.volume = 0.0
        self.play_calls = []
        self.stopped = False

    def set_volume(self, volume):
        self.volume = volume

    def play(self, sound, loops=0, fade_ms=0):
        self.play_calls.append({"sound": sound, "loops": loops, "fade_ms": fade_ms})
        self.busy = True
        self.stopped = False

    def get_busy(self):
        return self.busy

    def fadeout(self, milliseconds):
        self.busy = False

    def stop(self):
        self.busy = False
        self.stopped = True


class AudioBehaviourTests(unittest.TestCase):
    def test_wheel_squeal_fades_in_between_10_and_15_kmh_at_low_level(self):
        audio = AudioSystem.__new__(AudioSystem)
        audio.wheel_squeal_supported = True
        audio.wheel_squeal_sound = object()
        audio.wheel_squeal_channel = FakeChannel()
        audio._wheel_squeal_volume = 0.0

        audio._update_wheel_squeal(SimpleNamespace(speed=12.5 / 3.6), 1.0)

        self.assertGreater(audio._wheel_squeal_volume, 0.0)
        self.assertLess(audio._wheel_squeal_volume, 0.1)
        self.assertEqual(audio.wheel_squeal_channel.play_calls[0]["loops"], -1)

    def test_wheel_squeal_is_capped_at_point_one(self):
        audio = AudioSystem.__new__(AudioSystem)
        audio.wheel_squeal_supported = True
        audio.wheel_squeal_sound = object()
        audio.wheel_squeal_channel = FakeChannel()
        audio._wheel_squeal_volume = 0.0

        audio._update_wheel_squeal(SimpleNamespace(speed=25.0 / 3.6), 10.0)

        self.assertAlmostEqual(audio._wheel_squeal_volume, 0.1, places=3)
        self.assertAlmostEqual(audio.wheel_squeal_channel.volume, 0.1, places=3)

    def test_light_and_medium_brakes_loop_without_repetition_gaps(self):
        for notch, sound_key in ((1, "gentle"), (2, "medium")):
            with self.subTest(notch=notch):
                audio = AudioSystem.__new__(AudioSystem)
                audio.brake_sounds = {"gentle": object(), "medium": object()}
                audio.brake_channel = FakeChannel()
                audio.brake_channel_alt = FakeChannel()
                audio._active_brake_channel = 0
                audio._brake_stop_fade_done = False
                audio._was_braking = False
                audio._played_near_stop = False
                audio._last_brake_notch = 0
                audio._brake_repeat_timer = 0.0
                audio._brake_target_volume = 0.0
                train = SimpleNamespace(
                    speed=20.0 / 3.6,
                    emergency_brake_active=False,
                    controller_notch=-notch,
                )

                audio._update_brakes(train, 1 / 60)

                active = (audio.brake_channel, audio.brake_channel_alt)[
                    audio._active_brake_channel
                ]
                self.assertEqual(active.play_calls[0]["loops"], -1)


if __name__ == "__main__":
    unittest.main()
