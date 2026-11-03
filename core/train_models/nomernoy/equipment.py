"""81-717 system adapters.

Detailed equipment parameters remain pending a 81-717 technical source. Until
then this model uses explicitly normalized fallback systems, not 81-760 values.
"""
from core.train_models.shared.provisional_equipment import (
    ConfiguredTraction, ProvisionalElectrodynamicBrake, ProvisionalPneumaticSystem,
)


class NomernoyPneumatics(ProvisionalPneumaticSystem):
    pass


class NomernoyElectrodynamicBrake(ProvisionalElectrodynamicBrake):
    pass


class NomernoyTraction(ConfiguredTraction):
    pass
