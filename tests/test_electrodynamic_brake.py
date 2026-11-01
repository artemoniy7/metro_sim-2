from core.electrodynamic_brake import ElectrodynamicBrake


def test_three_current_steps_are_40_65_and_100_percent():
    brake = ElectrodynamicBrake()
    speed = 60 / 3.6
    values = [brake.calculate(speed, notch) for notch in (-1, -2, -3)]
    assert values[0] == values[2] * 0.4
    assert values[1] == values[2] * 0.65


def test_electric_brake_switches_off_at_five_kmh():
    brake = ElectrodynamicBrake()
    assert brake.calculate(60 / 3.6, -3) > brake.calculate(20 / 3.6, -3)
    assert brake.calculate(5 / 3.6, -3) == 0.0


def test_rheostatic_mode_is_used_when_regeneration_is_unavailable():
    brake = ElectrodynamicBrake()
    assert brake.calculate(40 / 3.6, -3, regeneration_available=False) > 0
    assert brake.mode == "rheostatic"


def test_failed_electric_brake_has_no_electric_deceleration():
    brake = ElectrodynamicBrake()
    assert brake.calculate(60 / 3.6, -3, available=False) == 0.0
