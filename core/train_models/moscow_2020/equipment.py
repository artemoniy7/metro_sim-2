"""Provisional 81-777 equipment until model-specific technical data is added."""
from core.train_models.shared.provisional_equipment import (
    ConfiguredTraction, ProvisionalElectrodynamicBrake, ProvisionalPneumaticSystem,
)


class Moscow2020Pneumatics(ProvisionalPneumaticSystem):
    """Normalized pneumatic fallback; not manufacturer pressure values."""


class Moscow2020ElectrodynamicBrake(ProvisionalElectrodynamicBrake):
    """ED braking remains disabled until its speed/force curve is sourced."""


class Moscow2020Traction(ConfiguredTraction):
    """Uses the provisional traction-notch curve from the train data file."""
