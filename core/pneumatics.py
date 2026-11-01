"""Simplified 81-760/761 pneumatic equipment model.

Pressures use kgf/cm². Setpoints and circuit layout follow the supplied
training material. Flow coefficients are simulation approximations.
"""
class PneumaticSystem:
    NM_COMPRESSOR_ON = 6.5
    NM_COMPRESSOR_OFF = 8.0
    TM_CHARGED_PRESSURE = 5.2
    TM_SERVICE_PRESSURES = {-1: 4.4, -2: 4.1, -3: 3.1}
    TC_EMPTY_MAX = 2.35
    TC_LOADED_MAX = 3.45

    def __init__(self, loaded=False):
        self.pressure_nm = 7.5
        self.pressure_tm = self.TM_CHARGED_PRESSURE
        self.pressure_tc = 0.0
        self.pressure_door = 5.1
        self.pressure_parking = 7.5
        self.air_spring_pressures = [2.2, 2.2, 2.2, 2.2]
        self.loaded = bool(loaded)
        self.compressor_active = False
        self.parking_brake_commanded = False
        self.emergency_vent_active = False
        self._last_tm_pressure = self.pressure_tm
        self._previous_tc = self.pressure_tc

    @property
    def brake_applied(self):
        return self.pressure_tc > 0.1

    @property
    def doors_available(self):
        return self.pressure_door >= 4.9

    @property
    def parking_brake_applied(self):
        return self.pressure_parking < 6.3

    def _target_tm_pressure(self, notch, emergency):
        if emergency:
            return 0.0
        if notch < 0:
            return self.TM_SERVICE_PRESSURES[max(-3, min(-1, notch))]
        return self.TM_CHARGED_PRESSURE

    def _target_tc_pressure(self, notch, emergency):
        if emergency:
            return self.TC_LOADED_MAX if self.loaded else self.TC_EMPTY_MAX
        if notch >= 0:
            return 0.0
        reduction = max(0.0, self.TM_CHARGED_PRESSURE - self.pressure_tm)
        target = min(self.TC_EMPTY_MAX, reduction * 1.12)
        return target * (self.TC_LOADED_MAX / self.TC_EMPTY_MAX) if self.loaded else target

    def update(self, dt, controller_notch=0, emergency=False,
               parking_brake_commanded=False):
        if dt <= 0:
            return
        dt = min(float(dt), 0.1)
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

        target_tm = self._target_tm_pressure(controller_notch, emergency)
        if target_tm < self.pressure_tm:
            self.pressure_tm = max(
                target_tm, self.pressure_tm - (4.5 if emergency else 0.9) * dt
            )
        elif target_tm > self.pressure_tm:
            self.pressure_tm = min(target_tm, self.pressure_tm + 0.65 * dt)

        target_tc = self._target_tc_pressure(controller_notch, emergency)
        if self.pressure_nm < 4.0:
            target_tc = min(target_tc, self.pressure_nm * 0.55)
        if target_tc > self.pressure_tc:
            self.pressure_tc = min(target_tc, self.pressure_tc + 0.75 * dt)
        elif target_tc < self.pressure_tc:
            self.pressure_tc = max(target_tc, self.pressure_tc - 0.48 * dt)

        # Approximate whole-consist air consumption; source material gives no
        # per-frame flow coefficient.
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
        self.pressure_tc = max(0.0, min(self.TC_LOADED_MAX, self.pressure_tc))
        self.pressure_door = max(0.0, min(5.1, self.pressure_door))
        self.pressure_parking = max(0.0, min(8.2, self.pressure_parking))
