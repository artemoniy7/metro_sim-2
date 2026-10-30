"""Simple AI traffic travelling against the main line direction."""
from core.train import Train


class OpposingBot:
    """A lightweight reverse-direction train with station stops."""

    def __init__(self, train_data, start_position):
        self.train = Train(train_data)
        self.train.position = float(start_position)
        self.train.direction = -1
        self.train.track_index = 0
        self.train.is_bot = True
        self.train.is_opposing_bot = True
        self.state = "running"
        self.target_station = None
        self.dwell_timer = 0.0

    def _next_station(self, line):
        candidates = [
            station for station in line.stations
            if float(station.get("position", 0)) < self.train.position - 3.0
        ]
        return max(candidates, key=lambda item: float(item.get("position", 0)), default=None)

    def update(self, dt, line):
        train = self.train
        dt = min(max(0.0, dt), 0.1)
        if dt <= 0:
            return
        if self.state == "dwelling":
            train.controller_notch = 0
            train.speed = 0.0
            train.acceleration_state = 0.0
            train.doors_open = True
            self.dwell_timer -= dt
            if self.dwell_timer <= 0.0:
                self.state = "running"
                self.target_station = None
                train.doors_open = False
            else:
                return

        station = self._next_station(line)
        self.target_station = station
        distance = (train.position - float(station.get("position", 0))
                    if station is not None else float("inf"))
        speed = max(0.0, train.speed)
        stopping_distance = speed * speed / (2.0 * 0.85) + speed * 1.8 + 22.0
        target_speed = min(train.max_speed, 72.0 / 3.6)

        if station is not None and distance <= 3.0 and speed <= 0.8:
            train.position = float(station.get("position", train.position))
            train.speed = 0.0
            train.acceleration_state = 0.0
            train.controller_notch = 0
            train.doors_open = True
            self.state = "dwelling"
            self.dwell_timer = float(station.get("dwell_seconds", 20))
            return

        if station is not None and distance <= stopping_distance:
            train.controller_notch = -3 if speed > 4.0 else -2
        elif speed < target_speed - 0.3:
            train.controller_notch = 4
        elif speed > target_speed + 0.3:
            train.controller_notch = -1
        else:
            train.controller_notch = 0

        train.doors_open = False
        train.update(dt, line)
