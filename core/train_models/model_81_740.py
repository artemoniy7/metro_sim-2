"""Model adapter for the 81-740 'Rusich'."""
from core.train import Train
from core.train_models.rusich.equipment import (
    RusichPneumatics, RusichElectrodynamicBrake, RusichTraction,
)


class Train81740(Train):
    model_id = "81-740"
    model_display_name = "Русич"
    physics_reference_status = "provisional_pending_technical_sources"
    PNEUMATIC_SYSTEM_CLASS = RusichPneumatics
    ELECTRODYNAMIC_BRAKE_CLASS = RusichElectrodynamicBrake
    TRACTION_SYSTEM_CLASS = RusichTraction
    ED_TO_PNEUMATIC_SPEED_KMH = 0.0
    PRESSURE_DISPLAY_UNIT = "усл. ед."
    PARKING_BRAKE_RELEASE_PRESSURE = 0.75
