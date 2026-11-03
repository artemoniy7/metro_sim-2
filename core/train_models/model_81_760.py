"""Model adapter for the 81-760/761 Oka train.

Its detailed traction, electrodynamic-brake and pneumatic behaviour is the
currently documented model implementation in core.train and its equipment
modules. Keep future 81-760-specific changes in this adapter/equipment layer.
"""
from core.train import Train


class Train81760(Train):
    model_id = "81-760"
    model_display_name = "Ока"
    physics_reference_status = "documented"
