"""KATP-2 traction response for the 81-760 model.

The high-speed fade preserves the existing calibrated game behaviour. It is
not presented as a complete motor torque curve.
"""
class KATP2Traction:
    def __init__(self, data=None):
        self.data = dict(data or {})

    def acceleration(self, notch, speed_mps, traction_notches):
        if notch <= 0 or not traction_notches:
            return 0.0
        index = min(len(traction_notches) - 1, int(notch) - 1)
        value = float(traction_notches[index])
        speed_kmh = max(0.0, float(speed_mps)) * 3.6
        fade = max(0.0, min(1.0, (speed_kmh - 40.0) / 40.0))
        return value * (1.0 - 0.92 * fade)
