from core.electrodynamic_brake import ElectrodynamicBrake


def test_three_current_steps_are_40_65_and_100_percent():
    brake = ElectrodynamicBrake()
    speed = 60 / 3.6
    values = [brake.calculate(speed, notch) for notch in (-1, -2, -3)]
    assert values[0] == values[2] * 0.4
    assert values[1] == values[2] * 0.65


def test_electric_brake_switches_off_at_five_kmh_without_unsupported_low_speed_fade():
    brake = ElectrodynamicBrake()
    at_20 = brake.calculate(20 / 3.6, -3)
    at_10 = brake.calculate(10 / 3.6, -3)
    assert brake.calculate(60 / 3.6, -3) > at_20
    assert at_10 == at_20
    assert brake.calculate(5 / 3.6, -3) == 0.0


def test_rheostatic_mode_is_used_when_regeneration_is_unavailable():
    brake = ElectrodynamicBrake()
    assert brake.calculate(40 / 3.6, -3, regeneration_available=False) > 0
    assert brake.mode == "rheostatic"


def test_failed_electric_brake_has_no_electric_deceleration():
    brake = ElectrodynamicBrake()
    assert brake.calculate(60 / 3.6, -3, available=False) == 0.0


class _Path:
    total_length = 10000.0

    @staticmethod
    def grade_acceleration(position):
        return 0.0


class _Line:
    path = _Path()

    @staticmethod
    def block_indication(position, train=None):
        return 80.0, 4


def test_train_uses_electric_brake_at_line_speed_and_friction_at_low_speed():
    from core.train import Train

    train = Train({"wagons": 2, "brake_mps2": 1.0})
    train.position = 1000.0
    train.speed = 60 / 3.6
    train.controller_notch = -3
    train.update(0.1, _Line())
    assert train.electrodynamic_brake.mode == "regenerative"
    assert train.pressure_tc == 0.0
    assert train.brake_deceleration > 0.9


def test_t3_brakes_from_60_to_7_kmh_in_reference_time_window():
    from core.train import Train

    train = Train({"wagons": 2, "brake_mps2": 1.0})
    train.position = 1000.0
    train.speed = 60 / 3.6
    train.controller_notch = -3
    elapsed = 0.0
    while train.speed * 3.6 > 7.0 and elapsed < 30.0:
        train.update(0.05, _Line())
        elapsed += 0.05
    assert train.speed * 3.6 <= 7.0
    assert 13.5 <= elapsed <= 14.5
    assert train.pressure_tc == 0.0 or train.speed * 3.6 <= 7.0


def test_train_stopping_distance_is_in_documented_service_brake_range():
    from core.train import Train

    train = Train({"wagons": 2, "brake_mps2": 1.0})
    train.position = 1000.0
    train.speed = 60 / 3.6
    train.controller_notch = -3
    start = train.position
    for _ in range(500):
        train.update(0.1, _Line())
        if train.speed <= 0.001:
            break
    distance = train.position - start
    assert 135.0 <= distance <= 190.0


def test_emergency_brake_effort_builds_with_pneumatic_cylinder_pressure():
    from core.train import Train

    train = Train({"wagons": 2, "brake_mps2": 1.0, "emergency_brake_mps2": 1.8})
    train.position = 1000.0
    train.speed = 60 / 3.6
    train.manual_emergency_brake_active = True
    train.update(0.1, _Line())
    assert train.pressure_tc > 0.0
    assert train.brake_deceleration < 0.5
    for _ in range(30):
        train.update(0.1, _Line())
    assert train.brake_deceleration > 1.6
