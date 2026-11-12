"""Playable train consist with traction, electrodynamic and pneumatic brakes."""
from core.wagon import Wagon
from core.als_ars import AlsArs
from core.train_models.oka.pneumatics import PneumaticSystem as OkaPneumaticSystem
from core.train_models.oka.electrodynamic_brake import ElectrodynamicBrake as OkaElectrodynamicBrake
from core.train_models.oka.traction import KATP2Traction


class Train:
    """Shared consist/route mechanics; equipment is injected by each model adapter."""
    model_id = "81-760"
    PNEUMATIC_SYSTEM_CLASS = OkaPneumaticSystem
    ELECTRODYNAMIC_BRAKE_CLASS = OkaElectrodynamicBrake
    TRACTION_SYSTEM_CLASS = KATP2Traction
    ED_TO_PNEUMATIC_SPEED_KMH = 7.0
    PRESSURE_DISPLAY_UNIT = "кгс/см²"
    PARKING_BRAKE_RELEASE_PRESSURE = 6.3
    MAX_COMBINED_SERVICE_DECELERATION = None

    def __init__(self, data=None):
        data = data or {}
        self.name = data.get("name", self.model_id)
        self.display_name = data.get("display_name", getattr(self, "model_display_name", self.name))
        self.max_speed = float(data.get("max_speed_kmh", 90)) / 3.6
        self.acceleration = float(data.get("acceleration_mps2", 0.9))
        self.service_brake = float(data.get("brake_mps2", 1.15))
        self.emergency_brake = float(data.get("emergency_brake_mps2", 1.4))
        self.jerk_limit = float(data.get("jerk_mps3", 0.45))
        self.brake_jerk_limit = float(data.get("brake_jerk_mps3", 0.6))
        self.traction_notches = [float(v) for v in data.get(
            "traction_notches_mps2", [0.25, 0.45, 0.68, self.acceleration]
        )]
        self.brake_notches = [float(v) for v in data.get(
            "brake_notches_mps2", [0.4, 0.65, 1.0]
        )]
        self.controller_notch = 0  # -3..-1 = T3..T1, 0 = coast, 1..4 = G1..G4
        car_count = max(2, int(data.get("wagons", 8)))
        self.wagons = [Wagon(self.name, i, is_loco=(i == 0 or i == car_count - 1))
                       for i in range(car_count)]
        self.loco_length_m = float(data.get("loco_length_m", 20.0))
        self.car_length_m = float(data.get("car_length_m", 19.0))
        self.position = 0.0
        self.speed = 0.0
        self.direction = 1
        # Player-controlled trains set this to -1/0/+1; AI trains leave it unset.
        self.reverser_position = None
        self.active_cab = 0
        self.track_index = 1
        self.track_change = None
        self.emergency_brake_active = False
        self.manual_emergency_brake_active = False
        self.overspeed_emergency_active = False
        self.overspeed_timer = 0.0
        self.OVERSPEED_GRACE_S = 3.6
        self.SPEED_MARGIN_KMH = 1.0
        self.acceleration_state = 0.0
        self.pneumatics = self.PNEUMATIC_SYSTEM_CLASS(
            loaded=bool(data.get("loaded", False))
        )
        self.pneumatics.set_load_fraction(float(data.get("load_fraction", 0.0)))
        self.electrodynamic_brake = self.ELECTRODYNAMIC_BRAKE_CLASS(
            data.get("electrodynamic_brake_max_mps2", self.ELECTRODYNAMIC_BRAKE_CLASS.MAX_SERVICE_DECELERATION)
        )
        self.traction_system = self.TRACTION_SYSTEM_CLASS(data)
        self.parking_brake_active = False
        self._brake_command_timer = 0.0
        self._was_brake_commanded = False
        self.brake_release_timer = 0.0
        self.BRAKE_RELEASE_SOUND_S = 1.0
        self.TRACTION_DELAY_AFTER_RELEASE_S = 1.0
        self.doors_open = False
        self.BRAKE_RESPONSE_DELAY_S = float(data.get("brake_response_delay_s", 0.0))
        self.rolling_resistance = 0.012
        self.speed_resistance = 0.00025
        self.als = AlsArs()
        self.electrodynamic_brake_failed = False
        self.regeneration_available = True
        self.brake_deceleration = 0.0

    @property
    def pressure_nm(self):
        return self.pneumatics.pressure_nm

    @property
    def pressure_tm(self):
        return self.pneumatics.pressure_tm

    @property
    def pressure_tc(self):
        return self.pneumatics.pressure_tc

    @property
    def brake_applied(self):
        return self.pneumatics.brake_applied or self.brake_deceleration > 0.05

    @property
    def consist_length_m(self):
        if not self.wagons:
            return self.loco_length_m
        return (self.loco_length_m * 2
                + max(0, len(self.wagons) - 2) * self.car_length_m)

    @property
    def occupied_track_indices(self):
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

    @property
    def brake_mode_label(self):
        if self.emergency_brake_active:
            return "Экстр. пневмо"
        if self.electrodynamic_brake.mode == "regenerative":
            return "ЭД: рекуперация"
        if self.electrodynamic_brake.mode == "rheostatic":
            return "ЭД: реостат"
        if self.pressure_tc > 0.1:
            return "Пневмо / удержание"
        return "Отпуск"

    def update(self, dt, line):
        if dt <= 0:
            return
        dt = min(dt, 0.1)
        limit = (self.max_speed if getattr(self, "is_opposing_bot", False)
                 else self.als.speed_limit(line, self.position, self.max_speed, self))
        self.current_speed_limit_mps = limit
        limit_kmh = limit * 3.6
        speed_kmh = abs(self.speed) * 3.6

        stronger_service_braking = self.controller_notch <= -2
        is_bot = bool(getattr(self, "is_bot", False))
        if is_bot:
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

        self.emergency_brake_active = bool(
            self.manual_emergency_brake_active
            or (self.overspeed_emergency_active and not is_bot)
        )
        grade_acceleration = line.path.grade_acceleration(self.position) * self.direction
        resistance = self.rolling_resistance + self.speed_resistance * self.speed
        natural_acceleration = (
            grade_acceleration - resistance if self.speed > 0 else grade_acceleration
        )

        brake_commanded = self.emergency_brake_active or self.controller_notch < 0
        if self._was_brake_commanded and not brake_commanded:
            if abs(self.speed) < 0.2 / 3.6:
                self.brake_release_timer = (
                    self.BRAKE_RELEASE_SOUND_S + self.TRACTION_DELAY_AFTER_RELEASE_S
                )
            else:
                self.brake_release_timer = 0.0
        self._brake_command_timer = (
            self._brake_command_timer + dt if brake_commanded else 0.0
        )
        self._was_brake_commanded = brake_commanded
        self.brake_release_timer = max(0.0, self.brake_release_timer - dt)

        # Ask the selected model's electric-brake implementation. Models whose
        # technical sources are still pending return zero here and use their
        # explicitly provisional pneumatic fallback instead.
        ed_available = (not self.electrodynamic_brake_failed
                        and self.electrodynamic_brake.available)
        ed_deceleration = 0.0
        if not self.emergency_brake_active:
            ed_deceleration = self.electrodynamic_brake.calculate(
                self.speed, self.controller_notch,
                available=ed_available,
                regeneration_available=self.regeneration_available,
            )
        else:
            self.electrodynamic_brake.calculate(
                self.speed, 0, available=False
            )

        speed_kmh = abs(self.speed) * 3.6
        low_speed_replacement = (
            self.controller_notch if self.controller_notch < 0
            and (speed_kmh <= self.ED_TO_PNEUMATIC_SPEED_KMH or not ed_available) else 0
        )
        hold_brake = (
            self.speed <= 1.8 / 3.6 and self.controller_notch <= 0
            and not self.emergency_brake_active and not self.parking_brake_active
        )
        self.pneumatics.update(
            dt,
            controller_notch=self.controller_notch,
            emergency=self.emergency_brake_active,
            parking_brake_commanded=self.parking_brake_active,
            service_brake_notch=low_speed_replacement,
            hold_brake=hold_brake,
        )

        # Convert the selected model's cylinder pressure into its configured
        # service-brake contribution. Provisional models use normalized units;
        # Oka uses its documented circuit model plus game calibration.
        friction_fraction = (
            self.pressure_tc / max(0.01, self.pneumatics.max_tc_pressure)
        )
        friction_deceleration = self.service_brake * friction_fraction
        parking_threshold = max(0.01, float(self.PARKING_BRAKE_RELEASE_PRESSURE))
        parking_fraction = max(
            0.0, min(1.0, (parking_threshold - self.pneumatics.pressure_parking) / parking_threshold)
        )
        parking_deceleration = self.service_brake * parking_fraction

        if self.emergency_brake_active:
            # Emergency effort is pneumatic and follows actual cylinder build-up;
            # it is not an instantaneous, pressure-independent deceleration.
            deceleration = self.emergency_brake * friction_fraction
        else:
            deceleration = ed_deceleration + friction_deceleration
        deceleration = max(deceleration, parking_deceleration)
        # Some model adapters publish a maximum combined brake effort. This
        # prevents ED + pneumatic blending from exceeding that calibrated cap.
        combined_brake_limit = self.MAX_COMBINED_SERVICE_DECELERATION
        if combined_brake_limit is not None:
            deceleration = min(deceleration, float(combined_brake_limit))
        self.brake_deceleration = deceleration

        if deceleration > 0.0:
            target_acceleration = -deceleration + grade_acceleration - resistance
            jerk = self.brake_jerk_limit if target_acceleration < self.acceleration_state else self.jerk_limit
            change = jerk * dt
            self.acceleration_state += max(
                -change, min(change, target_acceleration - self.acceleration_state)
            )
            self.speed = max(0.0, self.speed + self.acceleration_state * dt)
            if self.speed <= 0.0:
                self.acceleration_state = 0.0
        else:
            permitted_speed = limit + self.SPEED_MARGIN_KMH / 3.6
            if self.speed > permitted_speed:
                self.speed = max(permitted_speed, self.speed - self.service_brake * dt)
                self.acceleration_state = min(0.0, self.acceleration_state)
            else:
                target_acceleration = natural_acceleration
                traction_released = self.pressure_tc <= 0.01
                if (self.controller_notch > 0 and traction_released
                        and not self.pneumatics.parking_brake_applied
                        and not self.doors_open and self.brake_release_timer <= 0.0
                        and getattr(self, "reverser_position", None) != 0):
                    traction_acceleration = self.traction_system.acceleration(
                        self.controller_notch, self.speed, self.traction_notches
                    )
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
