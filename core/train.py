"""Playable train consist with a notched traction/brake controller."""
from core.wagon import Wagon
from core.als_ars import AlsArs


class Train:
    def __init__(self, data=None):
        data = data or {}
        self.name = data.get("name", "81-760")
        self.display_name = data.get("display_name", self.name)
        self.max_speed = float(data.get("max_speed_kmh", 90)) / 3.6
        self.acceleration = float(data.get("acceleration_mps2", 0.9))
        self.service_brake = float(data.get("brake_mps2", 1.15))
        self.emergency_brake = float(data.get("emergency_brake_mps2", 1.4))
        self.jerk_limit = float(data.get("jerk_mps3", 0.45))
        # Per-notch values are configured per train, in m/s².
        self.traction_notches = [float(v) for v in data.get(
            "traction_notches_mps2", [0.25, 0.45, 0.68, self.acceleration]
        )]
        self.brake_notches = [float(v) for v in data.get(
            "brake_notches_mps2", [0.45, 0.75, self.service_brake]
        )]
        self.controller_notch = 0  # -3..-1 = T3..T1, 0 = coast, 1..4 = G1..G4
        car_count = max(2, int(data.get("wagons", 8)))
        # Two cab cars at the ends, with six passenger cars between them.
        self.wagons = [Wagon(self.name, i, is_loco=(i == 0 or i == car_count - 1))
                       for i in range(car_count)]
        self.loco_length_m = float(data.get("loco_length_m", 20.0))
        self.car_length_m = float(data.get("car_length_m", 19.0))
        self.position = 0.0
        self.speed = 0.0
        # +1 follows the line towards the terminus; -1 runs against it.
        self.direction = 1
        # Track 1 is the original/main path; adjacent tracks are reached only
        # through a reserved crossover in TrackNetwork.
        self.track_index = 1
        self.track_change = None
        self.emergency_brake_active = False
        self.manual_emergency_brake_active = False
        self.overspeed_emergency_active = False
        self.overspeed_timer = 0.0
        self.OVERSPEED_GRACE_S = 3.6
        self.SPEED_MARGIN_KMH = 1.0
        self.acceleration_state = 0.0
        # Pneumatic brake circuit pressures (kgf/cm²).
        self.pressure_nm = 7.5  # Main reservoir (compressor recovery below 6.0).
        self.pressure_tm = 5.0  # Brake pipe: charged in the released state.
        self.pressure_tc = 0.0  # Brake cylinders: empty when released.
        # Compatibility flag for systems that still inspect this property.
        # Braking force itself is calculated from pressure_tc below.
        self.brake_applied = False
        self._brake_command_timer = 0.0
        self._was_brake_commanded = False
        self.brake_release_timer = 0.0
        self.BRAKE_RELEASE_SOUND_S = 4.0
        self.TRACTION_DELAY_AFTER_RELEASE_S = 1.5
        self.doors_open = False
        self.BRAKE_RESPONSE_DELAY_S = float(data.get("brake_response_delay_s", 0.0))
        # Small rolling/air resistance: noticeable over time, but not a hard brake.
        self.rolling_resistance = 0.012  # m/s² at low speed
        self.speed_resistance = 0.00025  # additional m/s² per m/s
        self.als = AlsArs()

    @property
    def consist_length_m(self):
        if not self.wagons:
            return self.loco_length_m
        return (self.loco_length_m * 2
                + max(0, len(self.wagons) - 2) * self.car_length_m)

    @property
    def occupied_track_indices(self):
        """Tracks physically occupied while the consist is crossing a switch."""
        if self.track_change:
            return {self.track_change["from"], self.track_change["to"]}
        return {self.track_index}

    @property
    def controller_label(self):
        if self.controller_notch < 0:
            return f"T{abs(self.controller_notch)}"
        if self.controller_notch > 0:
            return f"G{self.controller_notch}"
        return "0 (перекрыша)"

    def update(self, dt, line):
        if dt <= 0:
            return
        dt = min(dt, 0.1)
        limit = (self.max_speed if getattr(self, "is_opposing_bot", False)
                 else self.als.speed_limit(line, self.position, self.max_speed, self))
        self.current_speed_limit_mps = limit
        limit_kmh = limit * 3.6
        speed_kmh = abs(self.speed) * 3.6

        # Overspeed emergency trip is active in T1 (or when not using
        # stronger service braking). Selecting T2/T3 suppresses the emergency
        # trip because the driver is already applying stronger service braking.
        stronger_service_braking = self.controller_notch <= -2
        is_bot = bool(getattr(self, "is_bot", False))
        if is_bot:
            # AI drivers regulate speed themselves; don't latch the emergency
            # brake for them. The normal permitted-speed supervision below still
            # limits speed, and manual emergency braking remains available.
            self.overspeed_timer = 0.0
            self.overspeed_emergency_active = False
        elif stronger_service_braking:
            self.overspeed_timer = 0.0
        elif not self.overspeed_emergency_active:
            if speed_kmh > limit_kmh:
                self.overspeed_timer += dt
                if self.overspeed_timer >= self.OVERSPEED_GRACE_S:
                    self.overspeed_emergency_active = True
            else:
                self.overspeed_timer = 0.0

        # Player trains retain emergency protection; AI trains use regular
        # speed supervision so a brief overspeed cannot permanently immobilize them.
        self.emergency_brake_active = bool(
            self.manual_emergency_brake_active
            or (self.overspeed_emergency_active and not is_bot)
        )
        grade_acceleration = line.path.grade_acceleration(self.position) * self.direction
        resistance = self.rolling_resistance + self.speed_resistance * self.speed
        # Positive grade acceleration means gravity helps the train move forward.
        natural_acceleration = grade_acceleration - resistance if self.speed > 0 else grade_acceleration

        # Pneumatic brake response is modeled through brake-pipe and
        # brake-cylinder pressures, with an immediate emergency override.
        brake_commanded = self.emergency_brake_active or self.controller_notch < 0
        if self._was_brake_commanded and not brake_commanded:
            if abs(self.speed) < 0.2 / 3.6:
                self.brake_release_timer = (
                    self.BRAKE_RELEASE_SOUND_S + self.TRACTION_DELAY_AFTER_RELEASE_S
                )
            else:
                self.brake_release_timer = 0.0
        if brake_commanded:
            self._brake_command_timer += dt
        else:
            self._brake_command_timer = 0.0
        self._was_brake_commanded = brake_commanded
        self.brake_release_timer = max(0.0, self.brake_release_timer - dt)

        # Track air usage from the main reservoir as the brake circuit changes.
        previous_tm_pressure = self.pressure_tm
        previous_tc_pressure = self.pressure_tc

        # 1. Brake-pipe pressure follows the controller and emergency circuit.
        if self.controller_notch < 0 or self.emergency_brake_active:
            target_tm = 0.0 if self.emergency_brake_active else 3.0
        else:
            target_tm = 5.0

        pressure_tm_step = 2.0 * dt
        if self.pressure_tm > target_tm:
            self.pressure_tm = max(target_tm, self.pressure_tm - pressure_tm_step)
        elif self.pressure_tm < target_tm:
            self.pressure_tm = min(target_tm, self.pressure_tm + pressure_tm_step)

        # 2. Cylinder pressure builds only for a service-brake command.
        if self.emergency_brake_active:
            # The safety loop applies the emergency pressure immediately.
            self.pressure_tc = 3.5
        else:
            if self.controller_notch < 0 and self.pressure_tm < 4.5:
                brake_level = min(3, abs(self.controller_notch))
                target_tc = 2.3 + (brake_level - 1) * 0.6
            else:
                target_tc = 0.0

            if self.pressure_tc < target_tc:
                self.pressure_tc = min(target_tc, self.pressure_tc + 1.5 * dt)
            elif self.pressure_tc > target_tc:
                self.pressure_tc = max(target_tc, self.pressure_tc - 1.0 * dt)

        # Filling the brake cylinders and recharging the brake pipe consume
        # air from the main reservoir. The coefficients are simplified so the
        # reservoir pressure falls enough to trigger the compressor naturally.
        cylinder_air_used = max(0.0, self.pressure_tc - previous_tc_pressure)
        pipe_air_used = max(0.0, self.pressure_tm - previous_tm_pressure)
        self.pressure_nm -= cylinder_air_used * 2.5 + pipe_air_used * 0.8

        # The compressor starts below 7.0 kgf/cm² and restores the reservoir
        # towards 8.0 kgf/cm²; AudioSystem plays the matching recordings.
        if self.pressure_nm < 7.0:
            self.pressure_nm = min(8.0, self.pressure_nm + 0.5 * dt)
        elif self.pressure_nm > 8.0:
            self.pressure_nm = 8.0

        self.pressure_tm = max(0.0, min(5.0, self.pressure_tm))
        self.pressure_tc = max(0.0, min(3.5, self.pressure_tc))
        self.pressure_nm = max(0.0, self.pressure_nm)
        self.brake_applied = self.pressure_tc > 0.1

        # Cylinder pressure determines service braking; emergency uses its
        # configured maximum deceleration independently of cylinder ramping.
        deceleration = self.pressure_tc * 0.35
        if self.emergency_brake_active:
            deceleration = self.emergency_brake

        if deceleration > 0.0:
            target_acceleration = -deceleration + grade_acceleration - resistance
            change = self.jerk_limit * dt
            self.acceleration_state += max(
                -change, min(change, target_acceleration - self.acceleration_state)
            )
            self.speed = max(0.0, self.speed + self.acceleration_state * dt)
            if self.speed <= 0.0:
                self.acceleration_state = 0.0
        else:
            # Supervision brakes automatically if the train exceeds its permitted speed.
            permitted_speed = limit + self.SPEED_MARGIN_KMH / 3.6
            if self.speed > permitted_speed:
                self.speed = max(permitted_speed, self.speed - self.service_brake * dt)
                self.acceleration_state = min(0.0, self.acceleration_state)
            else:
                target_acceleration = natural_acceleration
                # Traction remains locked until the brake cylinders are fully
                # exhausted, including after an emergency brake application.
                traction_released = self.pressure_tc <= 0.01
                if (self.controller_notch > 0 and traction_released
                        and not self.doors_open and self.brake_release_timer <= 0.0):
                    index = min(len(self.traction_notches) - 1, self.controller_notch - 1)
                    traction_acceleration = self.traction_notches[index]
                    # Traction fades strongly at high speed. This makes the last
                    # 10 km/h before top speed take noticeably longer to gain.
                    speed_kmh = self.speed * 3.6
                    high_speed_fade = max(0.0, min(1.0, (speed_kmh - 40.0) / 40.0))
                    traction_acceleration *= 1.0 - 0.92 * high_speed_fade
                    target_acceleration += traction_acceleration
                if self.speed >= permitted_speed:
                    target_acceleration = min(0.0, target_acceleration)
                change = self.jerk_limit * dt
                self.acceleration_state += max(
                    -change, min(change, target_acceleration - self.acceleration_state)
                )
                permitted_speed = limit + self.SPEED_MARGIN_KMH / 3.6
                self.speed = max(
                    0.0, min(permitted_speed, self.speed + self.acceleration_state * dt)
                )

        self.position = min(line.path.total_length, max(
            0.0, self.position + self.direction * self.speed * dt
        ))
        reached_end = (self.position >= line.path.total_length if self.direction >= 0
                       else self.position <= 0.0)
        if reached_end:
            self.speed = 0.0
            self.acceleration_state = 0.0
