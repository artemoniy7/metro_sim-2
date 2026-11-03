"""Model adapter for the 81-777 train."""
from core.train import Train
from core.train_models.yauza.equipment import (
    YauzaPneumatics, YauzaElectrodynamicBrake, YauzaTraction,
)


class Train81777(Train):
    model_id = "81-777"
    model_display_name = "81-777"
    physics_reference_status = "provisional_pending_technical_sources"
    PNEUMATIC_SYSTEM_CLASS = YauzaPneumatics
    ELECTRODYNAMIC_BRAKE_CLASS = YauzaElectrodynamicBrake
    TRACTION_SYSTEM_CLASS = YauzaTraction
    ED_TO_PNEUMATIC_SPEED_KMH = 0.0
    PRESSURE_DISPLAY_UNIT = "усл. ед."
    PARKING_BRAKE_RELEASE_PRESSURE = 0.75
