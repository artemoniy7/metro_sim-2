"""Document-based electrodynamic brake model for 81-760/761."""

class ElectrodynamicBrake:
    BRAKE_CURRENT_FRACTIONS = {1: 0.40, 2: 0.65, 3: 1.00}
    MIN_SPEED_KMH = 5.0
    CURRENT_REDUCTION_START_KMH = 55.0
    CURRENT_REDUCTION_END_KMH = 20.0
    CURRENT_AT_20_KMH = 260.0
    ASSUMED_MAX_CURRENT_A = 300.0
    CURRENT_FRACTION_AT_20_KMH = CURRENT_AT_20_KMH / ASSUMED_MAX_CURRENT_A
    MAX_SERVICE_DECELERATION = 1.22

    def __init__(self, max_deceleration=None):
        self.max_deceleration = float(self.MAX_SERVICE_DECELERATION if max_deceleration is None else max_deceleration)
        self.available = True
        self.regeneration_available = True
        self.current_fraction = 0.0
        self.mode = "off"
        self.last_deceleration = 0.0

    @staticmethod
    def _speed_factor(speed_kmh):
        if speed_kmh <= ElectrodynamicBrake.MIN_SPEED_KMH:
            return 0.0
        if speed_kmh >= ElectrodynamicBrake.CURRENT_REDUCTION_START_KMH:
            return 1.0
        if speed_kmh >= ElectrodynamicBrake.CURRENT_REDUCTION_END_KMH:
            span = ElectrodynamicBrake.CURRENT_REDUCTION_START_KMH - ElectrodynamicBrake.CURRENT_REDUCTION_END_KMH
            progress = (speed_kmh - ElectrodynamicBrake.CURRENT_REDUCTION_END_KMH) / span
            return ElectrodynamicBrake.CURRENT_FRACTION_AT_20_KMH + (1.0 - ElectrodynamicBrake.CURRENT_FRACTION_AT_20_KMH) * progress
        return ElectrodynamicBrake.CURRENT_FRACTION_AT_20_KMH

    def calculate(self, speed_mps, controller_notch, available=None, regeneration_available=None):
        enabled = self.available if available is None else bool(available)
        regen = self.regeneration_available if regeneration_available is None else bool(regeneration_available)
        notch = abs(int(controller_notch)) if int(controller_notch) < 0 else 0
        speed_kmh = max(0.0, float(speed_mps)) * 3.6
        fraction = self.BRAKE_CURRENT_FRACTIONS.get(notch, 0.0)
        if not enabled or fraction <= 0.0 or speed_kmh <= self.MIN_SPEED_KMH:
            self.current_fraction = 0.0
            self.mode = "off"
            self.last_deceleration = 0.0
            return 0.0
        self.current_fraction = fraction * self._speed_factor(speed_kmh)
        self.mode = "regenerative" if regen else "rheostatic"
        self.last_deceleration = self.max_deceleration * self.current_fraction
        return self.last_deceleration
