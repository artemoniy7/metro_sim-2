"""Simplified 81-760/761 pneumatic equipment model.

Pressures use kgf/cm². Circuit architecture and nominal pressure setpoints are
based on the supplied 81-760/761 training material. Air-flow coefficients and
the game conversion from cylinder pressure to deceleration are approximations.
"""


class PneumaticSystem:
    NM_COMPRESSOR_ON = 6.5
    NM_COMPRESSOR_OFF = 8.0
    TM_CHARGED_PRESSURE = 5.2
    TM_SERVICE_PRESSURES = {-1: 4.4, -2: 4.1, -3: 3.1}
    TC_EMPTY_MAX = 2.35
    TC_LOADED_MAX = 3.45
    TC_FILL_RATE = 2.5
    TC_RELEASE_RATE = 0.48
    EMERGENCY_TM_VENT_RATE = 4.5
    HOLD_BRAKE_FRACTION = 0.65

    def __init__(self, loaded=False):
        self.pressure_nm = 7.5
        self.pressure_tm = self.TM_CHARGED_PRESSURE
        self.bogie_tc_pressures = [0.0, 0.0]
        self.pressure_door = 5.1
        self.pressure_parking = 7.5
        self.air_spring_pressures = [2.2, 2.2, 2.2, 2.2]
        self.load_fraction = 1.0 if loaded else 0.0
        self.compressor_active = False
        self.parking_brake_commanded = False
        self.emergency_vent_active = False
        self.anti_skid_timers = [0.0, 0.0]
        self._last_tm_pressure = self.pressure_tm
        self._previous_tc = 0.0

    @property
    def pressure_tc(self):
        return sum(self.bogie_tc_pressures) / len(self.bogie_tc_pressures)

    @pressure_tc.setter
    def pressure_tc(self, value):
        value = max(0.0, min(self.TC_LOADED_MAX, float(value)))
        self.bogie_tc_pressures = [value, value]

    @property
    def max_tc_pressure(self):
        return (self.TC_EMPTY_MAX
                + (self.TC_LOADED_MAX - self.TC_EMPTY_MAX) * self.load_fraction)

    @property
    def air_spring_target_pressure(self):
        # Training material: 2.2±0.2 empty and 3.8±0.2 loaded.
        return 2.2 + 1.6 * self.load_fraction

    @property
    def brake_applied(self):
        return self.pressure_tc > 0.1

    @property
    def doors_available(self):
        return self.pressure_door >= 4.9

    @property
    def parking_brake_applied(self):
        # Spring-applied brake: loss of control pressure applies it.
        return self.pressure_parking < 6.3

    @property
    def anti_skid_active(self):
        return any(timer > 0.0 for timer in self.anti_skid_timers)

    def set_load_fraction(self, fraction):
        """Set simulated car loading from empty (0.0) to full (1.0)."""
        self.load_fraction = max(0.0, min(1.0, float(fraction)))

    def trigger_anti_skid(self, bogie_index, duration=0.35):
        """Release one bogie's friction brake briefly after detected wheel slide."""
        index = max(0, min(1, int(bogie_index)))
        self.anti_skid_timers[index] = max(
            self.anti_skid_timers[index], max(0.05, float(duration))
        )

    def _target_tm_pressure(self, notch, emergency):
        if emergency:
            return 0.0
        if notch < 0:
            return self.TM_SERVICE_PRESSURES[max(-3, min(-1, notch))]
        return self.TM_CHARGED_PRESSURE

    def _target_tc_pressure(self, notch, emergency, hold_brake):
        if emergency:
            return self.max_tc_pressure
        if hold_brake and notch >= 0:
            return self.max_tc_pressure * self.HOLD_BRAKE_FRACTION
        if notch >= 0:
            return 0.0
        # BУФТ/АРП adjusts friction-brake pressure to loading. Three game
        # settings follow the documented 40/65/100% brake-current steps.
        fraction = { -1: 0.40, -2: 0.65, -3: 1.0 }[max(-3, min(-1, notch))]
        return self.max_tc_pressure * fraction

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
            if self.pressure_nm >= self.NM_COMPRESSOR_OFF:
                self.compressor_active = False
        elif self.pressure_nm <= self.NM_COMPRESSOR_ON:
            self.compressor_active = True
        if self.compressor_active:
            self.pressure_nm = min(8.0, self.pressure_nm + 0.5 * dt)
            if self.pressure_nm >= self.NM_COMPRESSOR_OFF:
                self.compressor_active = False

        target_tm = self._target_tm_pressure(notch, emergency)
        if target_tm < self.pressure_tm:
            rate = self.EMERGENCY_TM_VENT_RATE if emergency else 0.9
            self.pressure_tm = max(target_tm, self.pressure_tm - rate * dt)
        elif target_tm > self.pressure_tm:
            self.pressure_tm = min(target_tm, self.pressure_tm + 0.65 * dt)

        target_tc = self._target_tc_pressure(notch, emergency, hold_brake)
        if self.pressure_nm < 4.0:
            target_tc = min(target_tc, self.pressure_nm * 0.55)
        for index in range(2):
            if self.anti_skid_timers[index] > 0.0:
                self.anti_skid_timers[index] = max(0.0, self.anti_skid_timers[index] - dt)
                self.bogie_tc_pressures[index] = max(
                    0.0, self.bogie_tc_pressures[index] - 4.0 * dt
                )
            elif target_tc > self.bogie_tc_pressures[index]:
                self.bogie_tc_pressures[index] = min(
                    target_tc, self.bogie_tc_pressures[index] + self.TC_FILL_RATE * dt
                )
            elif target_tc < self.bogie_tc_pressures[index]:
                self.bogie_tc_pressures[index] = max(
                    target_tc, self.bogie_tc_pressures[index] - self.TC_RELEASE_RATE * dt
                )

        tc_fill = max(0.0, self.pressure_tc - self._previous_tc)
        tm_charge = max(0.0, self.pressure_tm - self._last_tm_pressure)
        self.pressure_nm = max(0.0, self.pressure_nm - tc_fill * 0.35 - tm_charge * 0.04)
        self._previous_tc = self.pressure_tc
        self._last_tm_pressure = self.pressure_tm

        door_target = min(5.1, self.pressure_nm)
        if self.pressure_door < door_target:
            self.pressure_door = min(door_target, self.pressure_door + 1.2 * dt)
        elif self.pressure_door > door_target:
            self.pressure_door = max(door_target, self.pressure_door - 1.0 * dt)

        parking_target = 0.0 if self.parking_brake_commanded else min(8.0, self.pressure_nm)
        if parking_target > self.pressure_parking:
            self.pressure_parking = min(parking_target, self.pressure_parking + 1.5 * dt)
        elif parking_target < self.pressure_parking:
            self.pressure_parking = max(parking_target, self.pressure_parking - 2.0 * dt)

        self.pressure_nm = min(9.0, self.pressure_nm)
        self.pressure_tm = max(0.0, min(5.8, self.pressure_tm))
        self.bogie_tc_pressures = [
            max(0.0, min(self.max_tc_pressure, value))
            for value in self.bogie_tc_pressures
        ]
        self.pressure_door = max(0.0, min(5.1, self.pressure_door))
        self.pressure_parking = max(0.0, min(8.2, self.pressure_parking))

        spring_target = self.air_spring_target_pressure
        for index, pressure in enumerate(self.air_spring_pressures):
            if pressure < spring_target:
                self.air_spring_pressures[index] = min(
                    spring_target, pressure + 0.55 * dt
                )
            elif pressure > spring_target:
                self.air_spring_pressures[index] = max(
                    spring_target, pressure - 0.55 * dt
                )
