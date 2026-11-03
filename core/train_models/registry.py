"""Explicit train-model dispatch.

Unknown model IDs fail loudly instead of silently receiving another train's
configuration. Add a dedicated adapter module and registry entry for each new
vehicle model.
"""
from core.train_models.model_81_717 import Train81717
from core.train_models.model_81_740 import Train81740
from core.train_models.model_81_760 import Train81760
from core.train_models.model_81_777 import Train81777

TRAIN_MODEL_CLASSES = {
    Train81717.model_id: Train81717,
    Train81740.model_id: Train81740,
    Train81760.model_id: Train81760,
    Train81777.model_id: Train81777,
}


def get_train_model_class(model_id):
    """Return the exact adapter for a model ID or raise a useful error."""
    key = str(model_id or "").strip()
    try:
        return TRAIN_MODEL_CLASSES[key]
    except KeyError as exc:
        supported = ", ".join(sorted(TRAIN_MODEL_CLASSES))
        raise ValueError(
            f"Unsupported train model {key!r}; supported models: {supported}"
        ) from exc


def create_train(data=None):
    """Build a train using the adapter matching its data model ID."""
    config = dict(data or {})
    configured_id = config.get("model_id")
    legacy_name = config.get("name")
    if configured_id and legacy_name and str(configured_id) != str(legacy_name):
        raise ValueError(
            f"Train config model_id {configured_id!r} does not match name {legacy_name!r}"
        )
    model_id = configured_id or legacy_name or "81-760"
    model_class = get_train_model_class(model_id)
    train = model_class(config)
    train.model_id = model_class.model_id
    train.physics_reference_status = model_class.physics_reference_status
    return train
