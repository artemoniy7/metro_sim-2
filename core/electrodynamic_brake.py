"""Compatibility import for legacy callers.

The authoritative 81-760 implementation now lives in
core.train_models.oka.electrodynamic_brake. Other train models inject their own
brake implementations.
"""
from core.train_models.oka.electrodynamic_brake import ElectrodynamicBrake

__all__ = ["ElectrodynamicBrake"]
