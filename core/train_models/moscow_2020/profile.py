"""Visual/audio profile for the 81-777 train."""
TRAIN_MODEL_ID = "81-777"
DISPLAY_NAME = "81-777"
ASSET_DIRECTORY = "81-777"
SPRITE_FILES = {
    "loco": "81-777-loco.png",
    "car": "81-777-car.png",
    "door_left": "81-777-door-left.png",
    "door_right": "81-777-door-right.png",
}
# Original sprite atlas dimensions.
LOCO_SOURCE_SIZE = (2130, 444)
CAR_SOURCE_SIZE = (2050, 431)

# Door openings are given as (left, top, right, bottom) in source-image pixels.
LOCO_DOOR_OPENINGS = (
    (362, 80, 560, 304),
    (832, 80, 1030, 304),
    (1314, 80, 1512, 304),
    (1785, 80, 1983, 304),
)
CAR_DOOR_OPENINGS = (
    (171, 66, 369, 290),
    (718, 66, 916, 290),
    (1211, 66, 1409, 290),
    (1716, 66, 1914, 290),
)
DOOR_LEFT_SIZE = (88, 225)
DOOR_RIGHT_SIZE = (87, 225)
DOOR_ANIMATION_DURATION_S = 3.0

# Door recordings stay model-specific. Motion recordings currently reuse the
# established 81-760/Oka set until model-specific 81-777 recordings are supplied.
AUDIO_DIRECTORY = "81-777"
MOTION_AUDIO_DIRECTORY = "81-760"
DOOR_ANIMATION_SUPPORTED = True

# Wheel-contact points scaled from the Oka atlas to the 81-777 source widths.
LOCO_PAIRS = ((359, 646), (1833, 2082))
CAR_PAIRS = ((193, 464), (1763, 2018))
JOINT_PATTERN = r"joint_stl760_(\d+)_([12])_(\d+)\.(?:wav|mp3)$"
STATION_JOINT_PATTERN = r"joint_station_(?:end_)?(\d+)_([12])_fade\.wav$"
COMPRESSOR_SUPPORTED = True
