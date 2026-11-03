# Train model separation and completion checklist

## Architecture rule

Every playable vehicle must be selected through `core.train_models.create_train()`.
The registry maps a stable model ID to a dedicated adapter module. Unknown model
IDs must raise an error; they must never silently inherit another model's setup.

Shared code belongs in `core.train.Train` only when it represents genuinely
common simulation mechanics (route position, consist geometry, speed state,
ALS-ARS integration and common game interfaces). Model-specific equipment and
behaviour belong in the corresponding `core/train_models/model_<id>.py` module
and its dedicated equipment modules.

## Current implementation

- [x] Add a strict model registry for 81-717, 81-740 and 81-760.
- [x] Route player, AI and opposing train construction through the registry.
- [x] Dispatch AI trains using the player's selected model instead of always
  forcing 81-760.
- [x] Add regression tests for distinct adapters and unknown-model rejection.
- [ ] Move each model's traction controller and traction physics into its own
  implementation.
- [ ] Give each model its own service-brake and emergency-brake implementation.
- [ ] Give each model its own pneumatic/electrical equipment implementation.
- [ ] Select train-specific audio profiles and asset directories.
- [ ] Select train-specific sprites, doors, geometry and animation.
- [ ] Validate all train JSON files against a schema and reject incomplete data.
- [ ] Add model-by-model integration tests and playable acceptance checks.

## Source and asset limitations found during the audit

### 81-760

The repository contains the 81-760/761 electrical and pneumatic implementation
and the associated training-source documentation. This remains the only model
whose detailed braking/equipment behaviour is currently documented in the
project materials.

### 81-717 and 81-740

Separate adapters now exist, but their detailed physical/equipment models are
not yet implemented. They intentionally retain the existing compatibility
baseline rather than inventing unsupported technical values. The current project
does not include their technical manuals.

### Graphics and sound

The train sprite folders for 81-717 and 81-740 contain instructions/placeholders,
not finished model sprites. The actual locomotive/car/door images are present
for 81-760 only. The train-specific sound directory currently exists only for
81-760. The renderer and audio system therefore still need explicit model
selection and verified model-specific assets before those trains can be called
visually/audio complete.

## Completion gate

Do not mark a train as complete until all of the following are true:

1. Its traction, coast and braking behaviour are implemented independently.
2. Its electrical and pneumatic systems match available technical sources.
3. Its HUD exposes only equipment that the model actually has.
4. Its sounds and sprites come from that model's asset profile.
5. AI and player trains use the same selected model implementation.
6. Unit tests cover its operating modes and transitions.
7. An in-game check confirms acceleration, stopping, doors, audio, rendering
   and AI behaviour without regressions to other train models.

Unknown technical values must be labelled as approximations or left pending;
they must not be presented as manufacturer specifications.
