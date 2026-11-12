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
    @staticmethod
    def make_audio():
        audio = AudioSystem.__new__(AudioSystem)
        audio.wheel_squeal_supported = True
        audio.wheel_squeal_sound = object()
        audio.wheel_squeal_channel = FakeChannel()
        audio._wheel_squeal_volume = 0.0
        return audio

    def test_wheel_squeal_is_silent_without_braking(self):
        audio = self.make_audio()

        audio._update_wheel_squeal(
            SimpleNamespace(speed=25.0 / 3.6, controller_notch=0,
                            emergency_brake_active=False),
            1.0,
        )

        self.assertEqual(audio._wheel_squeal_volume, 0.0)
        self.assertEqual(audio.wheel_squeal_channel.play_calls, [])

    def test_wheel_squeal_starts_above_15_kmh_during_braking(self):
        audio = self.make_audio()

        audio._update_wheel_squeal(
            SimpleNamespace(speed=17.5 / 3.6, controller_notch=-1,
                            emergency_brake_active=False),
            1.0,
        )

        self.assertGreater(audio._wheel_squeal_volume, 0.0)
        self.assertLess(audio._wheel_squeal_volume, 0.1)
        self.assertEqual(audio.wheel_squeal_channel.play_calls[0]["loops"], -1)

    def test_wheel_squeal_grows_with_brake_notch(self):
        volumes = []
        for notch in (1, 2, 3, 4):
            audio = self.make_audio()
            audio._update_wheel_squeal(
                SimpleNamespace(speed=25.0 / 3.6, controller_notch=-notch,
                                emergency_brake_active=(notch == 4)),
                10.0,
            )
            volumes.append(audio._wheel_squeal_volume)

        self.assertAlmostEqual(volumes[0], 0.06, places=3)
        self.assertEqual(volumes, sorted(volumes))
        self.assertAlmostEqual(volumes[-1], 0.16, places=3)

    def test_wheel_squeal_fades_out_at_high_speed(self):
        audio = self.make_audio()
        train = SimpleNamespace(
            speed=60.0 / 3.6,
            controller_notch=-3,
            emergency_brake_active=False,
        )

        audio._update_wheel_squeal(train, 10.0)
        self.assertGreater(audio._wheel_squeal_volume, 0.0)
        self.assertLess(audio._wheel_squeal_volume, 0.16)

        train.speed = 70.0 / 3.6
        audio._update_wheel_squeal(train, 10.0)
        self.assertEqual(audio._wheel_squeal_volume, 0.0)
        self.assertFalse(audio.wheel_squeal_channel.get_busy())

    def test_light_and_medium_brakes_loop_without_repetition_gaps(self):
        for notch in (1, 2):
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
