from core.electrodynamic_brake import ElectrodynamicBrake
from core.pneumatics import PneumaticSystem


def advance(system, seconds, **kwargs):
    for _ in range(round(seconds * 10)):
        system.update(0.1, **kwargs)


def test_electrodynamic_brake_has_three_documented_current_steps():
    brake = ElectrodynamicBrake()
    speed = 60 / 3.6
    t1 = brake.calculate(speed, -1)
    t2 = brake.calculate(speed, -2)
    t3 = brake.calculate(speed, -3)
    assert round(t1 / t3, 2) == 0.40
    assert round(t2 / t3, 2) == 0.65
    assert t3 == brake.max_deceleration


def test_electrodynamic_brake_fades_and_switches_off_at_five_kmh():
    brake = ElectrodynamicBrake()
    assert brake.calculate(60 / 3.6, -3) > brake.calculate(20 / 3.6, -3)
    assert brake.calculate(5 / 3.6, -3) == 0.0
    assert brake.mode == "off"


def test_electrodynamic_brake_uses_rheostatic_mode_without_regeneration():
    brake = ElectrodynamicBrake()
    assert brake.calculate(40 / 3.6, -3, regeneration_available=False) > 0
    assert brake.mode == "rheostatic"


def test_electric_brake_failure_requests_pneumatic_fallback():
    system = PneumaticSystem()
    advance(system, 2.0, service_brake_notch=-3)
    assert system.pressure_tc > 2.0


def test_three_pneumatic_settings_and_load_compensation():
    empty = PneumaticSystem()
    loaded = PneumaticSystem()
    loaded.set_load_fraction(1.0)
    advance(empty, 3.0, service_brake_notch=-3)
    advance(loaded, 3.0, service_brake_notch=-3)
    assert loaded.pressure_tc > empty.pressure_tc
    assert abs(
        empty.pressure_tc / empty.max_tc_pressure
        - loaded.pressure_tc / loaded.max_tc_pressure
    ) < 0.02


def test_anti_skid_releases_only_the_selected_bogie():
    system = PneumaticSystem()
    advance(system, 2.0, service_brake_notch=-3)
    before = system.bogie_tc_pressures[:]
    system.trigger_anti_skid(0)
    system.update(0.1, service_brake_notch=-3)
    assert system.bogie_tc_pressures[0] < before[0]
    assert system.bogie_tc_pressures[1] == before[1]


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


def test_air_suspension_regulators_follow_empty_and_loaded_pressure_targets():
    system = PneumaticSystem()
    advance(system, 2.0)
    assert all(abs(value - 2.2) < 0.01 for value in system.air_spring_pressures)
    system.set_load_fraction(1.0)
    advance(system, 3.0)
    assert all(abs(value - 3.8) < 0.01 for value in system.air_spring_pressures)
