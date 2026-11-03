"""Model adapter for the 81-717 'Nomernoy'."""
from core.train import Train
from core.train_models.nomernoy.equipment import (
    NomernoyPneumatics, NomernoyElectrodynamicBrake, NomernoyTraction,
)


class Train81717(Train):
    model_id = "81-717"
    model_display_name = "Номерной"
    physics_reference_status = "provisional_pending_technical_sources"
    PNEUMATIC_SYSTEM_CLASS = NomernoyPneumatics
    ELECTRODYNAMIC_BRAKE_CLASS = NomernoyElectrodynamicBrake
    TRACTION_SYSTEM_CLASS = NomernoyTraction
    ED_TO_PNEUMATIC_SPEED_KMH = 0.0
    PRESSURE_DISPLAY_UNIT = "усл. ед."
    PARKING_BRAKE_RELEASE_PRESSURE = 0.75
