"""Model adapter for the 81-740 'Rusich'.

This adapter deliberately does not borrow 81-760-specific claims. The current
movement/equipment implementation remains a compatibility baseline until
81-740 technical references are added and its systems are implemented here.
"""
from core.train import Train


class Train81740(Train):
    model_id = "81-740"
    model_display_name = "Русич"
    physics_reference_status = "pending_model_sources"
