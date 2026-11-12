"""Model-specific 81-777 equipment.

The published 1.1 m/s² maximum deceleration is used as the service-brake
calibration target. The detailed notch and speed curves below are explicit
simulation approximations because a factory brake-force curve was not found.
"""
from core.train_models.shared.provisional_equipment import (
    ConfiguredTraction, ProvisionalPneumaticSystem,
)


class Moscow2020Pneumatics(ProvisionalPneumaticSystem):
    """Normalized pneumatic fallback; values are not manufacturer pressures."""


class Moscow2020ElectrodynamicBrake:
    """Calibrated ED brake for 81-777; detailed curve remains approximate."""

    MAX_SERVICE_DECELERATION = 1.1
    MIN_SPEED_KMH = 5.0
    FULL_EFFORT_SPEED_KMH = 15.0

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
    """Uses the provisional traction-notch curve from the train data file."""
