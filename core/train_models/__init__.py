"""Train-model registry and lazy factory.

The factory imports concrete adapters only when called. This avoids a package
initialization cycle because the shared Train base imports model equipment
submodules during its own initialization.
"""


def create_train(data=None):
    from core.train_models.registry import create_train as factory
    return factory(data)


def get_train_model_class(model_id):
    from core.train_models.registry import get_train_model_class as resolver
    return resolver(model_id)


__all__ = ["create_train", "get_train_model_class"]
