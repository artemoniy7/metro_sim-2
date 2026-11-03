# Train model separation and completion checklist

## Architecture

Every playable vehicle is created through `core.train_models.create_train()`.
The registry selects a dedicated adapter by explicit `model_id`; mismatched or
unknown IDs fail immediately.

`core.train.Train` now owns only shared consist/route mechanics, speed state,
ALS-ARS integration and common game interfaces. It receives equipment classes
from each model adapter:

- pneumatic equipment;
- electrodynamic brake;
- traction response;
- pressure display units and brake-transition thresholds.

Each model also has its own renderer and audio profile. Missing model assets are
not silently replaced with another train's sprites or sounds.

## Current implementation

- [x] Strict registry and factory for 81-717, 81-740 and 81-760.
- [x] Player, AI and opposing trains use the selected model adapter.
- [x] Move the documented 81-760/761 pneumatic and electrodynamic-brake
  implementations into `core/train_models/oka/`.
- [x] Move the existing calibrated KATP-2 traction response into the Oka model.
- [x] Keep compatibility imports in the former `core/pneumatics.py` and
  `core/electrodynamic_brake.py` locations.
- [x] Give 81-717 and 81-740 separate pneumatic, ED-brake and traction adapters.
- [x] Use normalized, explicitly provisional equipment for 81-717 and 81-740;
  do not reuse Oka pressure values or claim their ED behaviour is modelled.
- [x] Add per-model sprite and audio profiles; select them after train creation.
- [x] Disable unverified wheel-joint geometry and door animation for models
  whose assets/geometry are not present.
- [x] Declare and validate explicit model IDs in all train configuration files.
- [x] Add regression tests for model dispatch, distinct equipment classes,
  provisional-vs-documented systems and config consistency.
- [ ] Replace 81-717 provisional equipment with source-verified systems.
- [ ] Replace 81-740 provisional equipment with source-verified systems.
- [ ] Add real 81-717 and 81-740 sprites, door geometry and audio recordings.
- [ ] Add model-specific traction/braking integration and in-game acceptance tests.

## Technical-source status

### 81-760/761 Ока

The Oka model retains the project implementation derived from the supplied
electrical and pneumatic training materials. The 1.22 m/s² ED calibration,
air-flow rates and other game-tuned values remain identified as calibrations or
approximations rather than certified manufacturer values.

### 81-717 Номерной and 81-740 Русич

The project materials available for this task do not include their technical
manuals. Their adapters therefore use normalized provisional pressure units
and a conservative pneumatic-only braking fallback. Their current traction
notch values remain the values already stored in their JSON files; these are
not certified performance curves. The adapters are separate so verified
equipment can replace each system without changing the other train models.

## Asset behaviour

- Oka uses only `assets/trains/81-760/` and
  `assets/sounds/train/81-760/`.
- Nomernoy uses only its `81-717` asset directories. No Oka fallback is used.
- Rusich uses only its `81-740` asset directories. No Oka fallback is used.
- If a model's files are absent, the renderer uses its generic car fallback and
  its audio profile remains silent for missing optional recordings.

## Completion gate

A model is not complete until its own technical sources, traction, service and
emergency braking, pneumatic/electrical systems, controller behaviour, HUD,
sprites, doors, sounds and AI operation have been checked together. Unknown
technical values must remain labelled provisional.
