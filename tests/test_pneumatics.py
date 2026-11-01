from core.pneumatics import PneumaticSystem


def advance(system, seconds, **kwargs):
    for _ in range(round(seconds * 10)):
        system.update(0.1, **kwargs)


def test_compressor_cut_in_and_cut_out():
    system = PneumaticSystem()
    system.pressure_nm = 6.4
    system.update(0.1)
    assert system.compressor_active
    system.pressure_nm = 7.99
    system.update(0.1)
    assert not system.compressor_active


def test_full_service_braking_reduces_tm_and_fills_cylinders():
    system = PneumaticSystem()
    advance(system, 3.0, controller_notch=-3)
    assert abs(system.pressure_tm - 3.1) < 0.15
    assert system.pressure_tc > 2.0


def test_brake_release_recharges_tm_and_exhausts_cylinders():
    system = PneumaticSystem()
    advance(system, 3.0, controller_notch=-3)
    advance(system, 7.0, controller_notch=0)
    assert system.pressure_tm > 4.8
    assert system.pressure_tc < 0.2


def test_parking_brake_is_spring_applied_and_air_released():
    system = PneumaticSystem()
    assert not system.parking_brake_applied
    advance(system, 5.0, parking_brake_commanded=True)
    assert system.parking_brake_applied
    advance(system, 6.0, parking_brake_commanded=False)
    assert not system.parking_brake_applied


def test_door_circuit_is_initially_charged():
    assert PneumaticSystem().doors_available
