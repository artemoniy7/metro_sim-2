"""Compatibility import for legacy callers.

The authoritative 81-760 implementation now lives in
core.train_models.oka.pneumatics. Other train models inject their own systems.
"""
from core.train_models.oka.pneumatics import PneumaticSystem

__all__ = ["PneumaticSystem"]
