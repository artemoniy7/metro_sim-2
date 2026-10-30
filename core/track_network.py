"""Three-lane, same-level track layout with safe crossover reservations.

Screen-space lane offsets are orthographic spacing only. They do not represent
elevation, tunnels at different depths, or stacked railway levels.
"""
class TrackNetwork:
    def __init__(self, line, data=None):
        data = data or {}
        self.line = line
        self.main_lane = int(data.get("main_lane", 1))
        self.lanes = list(data.get("lanes", [
            {"id": "left", "label": "Путь I", "offset_m": -3.43},
            {"id": "main", "label": "Главный путь", "offset_m": 0.0},
            {"id": "right", "label": "Путь III", "offset_m": 3.43},
        ]))
        if not self.lanes:
            self.lanes = [{"id": "main", "label": "Главный путь", "offset_px": 0,
                           "tint": [255, 255, 255]}]
        self.main_lane = max(0, min(len(self.lanes) - 1, self.main_lane))
        self.switch_length = max(40.0, float(data.get("switch_length_m", 100.0)))
        self.switch_window = max(self.switch_length, float(data.get("switch_window_m", 120.0)))
        spacing = max(300.0, float(data.get("switch_spacing_m", 1500.0)))
        first = max(100.0, float(data.get("first_switch_m", 900.0)))
        self.switches = [
            {"id": f"SW-{index:02d}", "position": position}
            for index, position in enumerate(
                self._positions(first, spacing, line.path.total_length), start=1
            )
        ]
        self.last_message = ""

    @staticmethod
    def _positions(first, spacing, total):
        position = first
        while position < total - 250.0:
            yield position
            position += spacing

    @staticmethod
    def _smoothstep(value):
        value = max(0.0, min(1.0, float(value)))
        return value * value * (3.0 - 2.0 * value)

    def lane_offset_for_index(self, index):
        index = max(0, min(len(self.lanes) - 1, int(index)))
        lane = self.lanes[index]
        # Store physical spacing in metres. Convert legacy pixel spacing using
        # the previous default camera scale to keep existing layouts compatible.
        if "offset_m" in lane:
            return float(lane["offset_m"])
        return float(lane.get("offset_px", 0.0)) / 28.0

    def lane_offset(self, train, position=None):
        change = getattr(train, "track_change", None)
        if not change:
            return self.lane_offset_for_index(train.track_index)
        position = float(train.position if position is None else position)
        span = max(0.001, change["end"] - change["start"])
        blend = self._smoothstep((position - change["start"]) / span)
        start = self.lane_offset_for_index(change["from"])
        end = self.lane_offset_for_index(change["to"])
        return start + (end - start) * blend

    def tint_for_train(self, train, position=None):
        change = getattr(train, "track_change", None)
        lane_index = train.track_index
        if change:
            position = float(train.position if position is None else position)
            blend = self._smoothstep(
                (position - change["start"]) / max(0.001, change["end"] - change["start"])
            )
            if blend >= 0.5:
                lane_index = change["to"]
        tint = self.lanes[max(0, min(len(self.lanes) - 1, lane_index))].get(
            "tint", [255, 255, 255]
        )
        return tuple(max(0, min(255, int(channel))) for channel in tint[:3])

    def lane_label(self, train):
        change = getattr(train, "track_change", None)
        if change:
            return (f"{self.lanes[change['from']].get('label', 'Путь')} → "
                    f"{self.lanes[change['to']].get('label', 'Путь')}")
        return str(self.lanes[train.track_index].get("label", "Путь"))

    def request_lane_change(self, train, direction, trains):
        if getattr(train, "track_change", None):
            self.last_message = "Сначала завершите перевод"
            return False
        source = int(train.track_index)
        target = source + (1 if direction > 0 else -1)
        if target < 0 or target >= len(self.lanes):
            self.last_message = "Соседнего пути нет"
            return False
        available = [
            switch for switch in self.switches
            if self.switch_length / 2 <= switch["position"] - train.position <= self.switch_window
        ]
        if not available:
            self.last_message = "Рядом нет стрелочного перевода"
            return False
        switch = min(available, key=lambda item: abs(item["position"] - train.position))
        zone_start = switch["position"] - self.switch_length
        zone_end = switch["position"] + self.switch_length
        conflicting_lanes = {source, target}
        for other in trains:
            if other is train or not hasattr(other, "position"):
                continue
            occupied = set(getattr(
                other, "occupied_track_indices", {getattr(other, "track_index", self.main_lane)}
            ))
            if not conflicting_lanes.intersection(occupied):
                continue
            front = float(other.position) + float(getattr(other, "loco_length_m", 0.0))
            rear = front - float(getattr(other, "consist_length_m", 0.0))
            if rear <= zone_end and front >= zone_start:
                self.last_message = "Стрелка занята другим составом"
                return False
        start = max(float(train.position), switch["position"] - self.switch_length / 2)
        end = switch["position"] + self.switch_length / 2
        if end <= start:
            self.last_message = "Стрелочный перевод уже пройден"
            return False
        train.track_change = {
            "from": source, "to": target,
            "start": start, "end": end, "switch": switch["id"],
        }
        self.last_message = f"Перевод на {self.lanes[target].get('label', 'соседний путь')}"
        return True

    def update_train(self, train):
        change = getattr(train, "track_change", None)
        if not change:
            return
        # Reserve both connected tracks until the tail of the consist clears.
        rear_position = float(train.position) - float(getattr(train, "consist_length_m", 0.0))
        if rear_position >= change["end"]:
            train.track_index = change["to"]
            train.track_change = None
            self.last_message = f"Занят {self.lanes[train.track_index].get('label', 'путь')}"
