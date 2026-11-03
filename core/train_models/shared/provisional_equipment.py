"""Non-certified fallback equipment used only while model manuals are missing.

Values here are normalized game units, not manufacturer pressure or current
specifications. The two unsupported models have their own adapters and can
replace these components independently when source material becomes available.
"""

class ProvisionalPneumaticSystem:
    UNIT_LABEL = "усл. ед."

    def __init__(self, loaded=False):
        self.pressure_nm = 1.0
        self.pressure_tm = 0.9
        self._pressure_tc = 0.0
        self.max_tc_pressure = 1.0
        self.bogie_tc_pressures = [0.0, 0.0]
        self.air_spring_pressures = [0.0, 0.0, 0.0, 0.0]
        self.anti_skid_timers = [0.0, 0.0]
        self.pressure_door = 1.0
        self.pressure_parking = 1.0
        self.compressor_active = False
        self.parking_brake_commanded = False
        self.emergency_vent_active = False
        self.load_fraction = 1.0 if loaded else 0.0

    @property
    def pressure_tc(self):
        return self._pressure_tc

    @pressure_tc.setter
    def pressure_tc(self, value):
        self._pressure_tc = max(0.0, min(self.max_tc_pressure, float(value)))
        self.bogie_tc_pressures = [self._pressure_tc, self._pressure_tc]

    @property
    def anti_skid_active(self):
        return any(timer > 0.0 for timer in self.anti_skid_timers)

    def trigger_anti_skid(self, bogie_index, duration=0.35):
        index = max(0, min(1, int(bogie_index)))
        self.anti_skid_timers[index] = max(self.anti_skid_timers[index], max(0.05, float(duration)))

    @property
    def brake_applied(self):
        return self.pressure_tc > 0.02

    @property
    def doors_available(self):
        return self.pressure_door >= 0.85

    @property
    def parking_brake_applied(self):
        return self.pressure_parking < 0.75

    def set_load_fraction(self, fraction):
        self.load_fraction = max(0.0, min(1.0, float(fraction)))

    def update(self, dt, controller_notch=0, emergency=False,
               parking_brake_commanded=False, service_brake_notch=None,
               hold_brake=False):
        if dt <= 0:
            return
        dt = min(float(dt), 0.1)
        notch = controller_notch if service_brake_notch is None else service_brake_notch
        self.parking_brake_commanded = bool(parking_brake_commanded)
        self.emergency_vent_active = bool(emergency)
        if self.compressor_active:
            if self.pressure_nm >= 1.0:
                self.compressor_active = False
        elif self.pressure_nm <= 0.72:
            self.compressor_active = True
        if self.compressor_active:
            self.pressure_nm = min(1.0, self.pressure_nm + 0.18 * dt)
        fraction = 1.0 if emergency else ({-1: 0.4, -2: 0.65, -3: 1.0}.get(max(-3, min(-1, notch)), 0.0) if notch < 0 else (0.55 if hold_brake else 0.0))
        target_tc = fraction * (0.85 + 0.15 * self.load_fraction)
        rate = 2.0 if target_tc > self.pressure_tc else 0.55
        if target_tc > self.pressure_tc:
            self.pressure_tc = min(target_tc, self.pressure_tc + rate * dt)
        else:
            self.pressure_tc = max(target_tc, self.pressure_tc - rate * dt)
        target_tm = 0.0 if emergency else (0.65 if notch < 0 else 0.9)
        self.pressure_tm += max(-1.2 * dt, min(0.8 * dt, target_tm - self.pressure_tm))
        target_door = self.pressure_nm
        self.pressure_door += max(-dt, min(dt, target_door - self.pressure_door))
        target_parking = 0.0 if self.parking_brake_commanded else self.pressure_nm
        self.pressure_parking += max(-1.5 * dt, min(1.5 * dt, target_parking - self.pressure_parking))
        self.pressure_nm = max(0.0, min(1.0, self.pressure_nm - max(0.0, self.pressure_tc - target_tc) * 0.02))


class ProvisionalElectrodynamicBrake:
    """No unsupported ED curve is assumed; service braking remains pneumatic."""
    MAX_SERVICE_DECELERATION = 0.0

    def __init__(self, max_deceleration=None):
        self.max_deceleration = 0.0
        self.available = False
        self.regeneration_available = False
        self.current_fraction = 0.0
        self.mode = "off"
        self.last_deceleration = 0.0

    def calculate(self, speed_mps, controller_notch, available=None,
                  regeneration_available=None):
        self.current_fraction = 0.0
        self.mode = "off"
        self.last_deceleration = 0.0
        return 0.0


class ConfiguredTraction:
    """Uses only the per-model traction notch values in that model's data file."""
    def __init__(self, data=None):
        self.data = dict(data or {})

    def acceleration(self, notch, speed_mps, traction_notches):
        if notch <= 0 or not traction_notches:
            return 0.0
        index = min(len(traction_notches) - 1, int(notch) - 1)
        return float(traction_notches[index])
