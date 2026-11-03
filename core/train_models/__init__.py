"""Train-model registry and factory.

Each supported train has its own adapter module. Shared route/consist mechanics
remain in core.train.Train; model-specific traction, braking, pneumatics, audio
and vehicle assets are progressively moved behind these adapters.
"""
from core.train_models.registry import create_train, get_train_model_class

__all__ = ["create_train", "get_train_model_class"]
