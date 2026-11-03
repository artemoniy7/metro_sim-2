"""Model adapter for the 81-760/761 Oka train."""
from core.train import Train
from core.train_models.oka.pneumatics import PneumaticSystem
from core.train_models.oka.electrodynamic_brake import ElectrodynamicBrake
from core.train_models.oka.traction import KATP2Traction


class Train81760(Train):
    model_id = "81-760"
    model_display_name = "Ока"
    physics_reference_status = "documented_with_game_calibrations"
    PNEUMATIC_SYSTEM_CLASS = PneumaticSystem
    ELECTRODYNAMIC_BRAKE_CLASS = ElectrodynamicBrake
    TRACTION_SYSTEM_CLASS = KATP2Traction
    ED_TO_PNEUMATIC_SPEED_KMH = 7.0
    PRESSURE_DISPLAY_UNIT = "кгс/см²"
