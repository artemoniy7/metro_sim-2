"""Model-specific 81-777 equipment.

The published 1.3 m/s² maximum acceleration and 1.1 m/s² maximum
deceleration are calibration targets. Detailed traction speed/notch curves
and brake curves remain explicit simulation approximations because
manufacturer force/current curves were not found.
"""
from core.train_models.shared.provisional_equipment import (
    ConfiguredTraction, ProvisionalPneumaticSystem,
)


class Moscow2020Pneumatics(ProvisionalPneumaticSystem):
    """Normalized pneumatic fallback; values are not manufacturer pressures."""


class Moscow2020ElectrodynamicBrake:
    """Calibrated ED brake for 81-777; detailed curve remains approximate."""

    MAX_SERVICE_DECELERATION = 1.1
    MIN_SPEED_KMH = 2.0
    FULL_EFFORT_SPEED_KMH = 8.0

    def __init__(self, max_deceleration=None):
        self.max_deceleration = float(
            self.MAX_SERVICE_DECELERATION
            if max_deceleration is None else max_deceleration
        )
        self.available = True
        self.regeneration_available = True
        self.current_fraction = 0.0
        self.mode = "off"
        self.last_deceleration = 0.0

    @classmethod
    def _speed_factor(cls, speed_kmh):
        if speed_kmh <= cls.MIN_SPEED_KMH:
            return 0.0
        if speed_kmh >= cls.FULL_EFFORT_SPEED_KMH:
            return 1.0
        return (
            (speed_kmh - cls.MIN_SPEED_KMH)
            / (cls.FULL_EFFORT_SPEED_KMH - cls.MIN_SPEED_KMH)
        )

    def calculate(self, speed_mps, controller_notch, available=None,
                  regeneration_available=None):
        enabled = self.available if available is None else bool(available)
        regen = (
            self.regeneration_available if regeneration_available is None
            else bool(regeneration_available)
        )
        notch = abs(int(controller_notch)) if int(controller_notch) < 0 else 0
        speed_kmh = max(0.0, float(speed_mps)) * 3.6
        if not enabled or notch == 0 or speed_kmh <= self.MIN_SPEED_KMH:
            self.current_fraction = 0.0
            self.mode = "off"
            self.last_deceleration = 0.0
            return 0.0

        # Linear notch scaling is a transparent game approximation, not a
        # published manufacturer current/torque table.
        notch_fraction = min(3, notch) / 3.0
        self.current_fraction = notch_fraction * self._speed_factor(speed_kmh)
        self.mode = "regenerative" if regen else "rheostatic"
        self.last_deceleration = self.max_deceleration * self.current_fraction
        return self.last_deceleration


class Moscow2020Traction(ConfiguredTraction):
    """Speed-tapered traction for the 81-777 simulation profile.

    The 1.3 m/s² low-speed maximum is based on the published train-family
    figure. Intermediate speed factors are provisional, not factory data.
    """

    # (speed in km/h, fraction of the configured notch effort).
    # The curve holds full effort at low speed, then tapers toward top speed.
    SPEED_EFFORT_CURVE = (
        (0.0, 1.0),
        (30.0, 1.0),
        (60.0, 0.75),
        (90.0, 0.35),
    )

    @classmethod
    def _speed_effort_factor(cls, speed_mps):
        speed_kmh = max(0.0, float(speed_mps)) * 3.6
        curve = cls.SPEED_EFFORT_CURVE
        if speed_kmh <= curve[0][0]:
            return curve[0][1]
        for (left_speed, left_factor), (right_speed, right_factor) in zip(
            curve, curve[1:]
        ):
            if speed_kmh <= right_speed:
                ratio = (speed_kmh - left_speed) / (right_speed - left_speed)
                return left_factor + ratio * (right_factor - left_factor)
        return curve[-1][1]

    def acceleration(self, notch, speed_mps, traction_notches):
        notch_effort = super().acceleration(notch, speed_mps, traction_notches)
        return notch_effort * self._speed_effort_factor(speed_mps)
