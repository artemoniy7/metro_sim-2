"""Model adapter for the 81-777 train."""
from core.train import Train
from core.train_models.moscow_2020.equipment import (
    Moscow2020Pneumatics, Moscow2020ElectrodynamicBrake, Moscow2020Traction,
)


class Train81777(Train):
    model_id = "81-777"
    model_display_name = "81-777"
    physics_reference_status = "partially_sourced_braking_calibration"
    PNEUMATIC_SYSTEM_CLASS = Moscow2020Pneumatics
    ELECTRODYNAMIC_BRAKE_CLASS = Moscow2020ElectrodynamicBrake
    TRACTION_SYSTEM_CLASS = Moscow2020Traction
    # ED effort is progressively handed over to the pneumatic brake near stop.
    # The exact crossover speed is a simulation calibration, not a factory value.
    ED_TO_PNEUMATIC_SPEED_KMH = 10.0
    MAX_COMBINED_SERVICE_DECELERATION = 1.1
    PRESSURE_DISPLAY_UNIT = "усл. ед."
    PARKING_BRAKE_RELEASE_PRESSURE = 0.75
