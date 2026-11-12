"""Tests for the reduced 81-777 braking audio mix."""

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
    def make_audio(self):
        audio = AudioSystem.__new__(AudioSystem)
        audio.brake_channel = FakeChannel()
        audio.brake_channel_alt = FakeChannel()
        audio.brake_release_sound = object()
        audio.brake_release_channel = FakeChannel()
        audio._was_braking = False
        audio._brake_stop_fade_done = False
        audio._played_near_stop = False
        audio._last_brake_notch = 0
        audio._brake_repeat_timer = 0.0
        audio._brake_target_volume = 0.0
        audio.wheel_squeal_channel = FakeChannel()
        audio._wheel_squeal_volume = 0.12
        return audio

    def test_braking_does_not_play_wheel_or_brake_squeal(self):
        audio = self.make_audio()
        audio.brake_channel.play_calls.clear()
        train = SimpleNamespace(
            speed=25.0 / 3.6,
            controller_notch=-3,
            emergency_brake_active=False,
        )

        audio._update_brakes(train, 1 / 60)
        audio._update_wheel_squeal(train, 1 / 60)

        self.assertEqual(audio.brake_channel.play_calls, [])
        self.assertEqual(audio.brake_channel_alt.play_calls, [])
        self.assertEqual(audio.wheel_squeal_channel.play_calls, [])
        self.assertTrue(audio.wheel_squeal_channel.stopped)
        self.assertEqual(audio._wheel_squeal_volume, 0.0)
        self.assertEqual(audio.brake_release_channel.play_calls, [])

    def test_pneumatic_release_sound_plays_when_brakes_release_at_standstill(self):
        audio = self.make_audio()
        audio._was_braking = True
        train = SimpleNamespace(
            speed=0.0,
            controller_notch=0,
            emergency_brake_active=False,
        )

        audio._update_brakes(train, 1 / 60)

        self.assertEqual(len(audio.brake_release_channel.play_calls), 1)
        self.assertIs(
            audio.brake_release_channel.play_calls[0]["sound"],
            audio.brake_release_sound,
        )
        self.assertEqual(audio.brake_release_channel.volume, 0.85)

    def test_pneumatic_release_sound_does_not_play_while_moving(self):
        audio = self.make_audio()
        audio._was_braking = True
        train = SimpleNamespace(
            speed=5.0 / 3.6,
            controller_notch=0,
            emergency_brake_active=False,
        )

        audio._update_brakes(train, 1 / 60)

        self.assertEqual(audio.brake_release_channel.play_calls, [])


if __name__ == "__main__":
    unittest.main()
