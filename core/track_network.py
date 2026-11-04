"""Parallel-track layout with local sidings and bidirectional crossovers."""
class TrackNetwork:
    def __init__(self, line, data=None):
        data = data or {}
        self.line = line
        self.main_lane = int(data.get("main_lane", 1))
        self.lanes = list(data.get("lanes", [
            {"id": "opposing", "label": "Встречный путь", "offset_m": -3.43, "direction": -1},
            {"id": "main", "label": "Главный путь", "offset_m": 0.0, "direction": 1},
        ]))
        if not self.lanes:
            self.lanes = [{"id": "main", "label": "Главный путь", "offset_m": 0.0}]
        self.main_lane = max(0, min(len(self.lanes) - 1, self.main_lane))
        self.switch_length = max(20.0, float(data.get("switch_length_m", 100.0)))
        self.switch_window = max(self.switch_length, float(data.get("switch_window_m", 120.0)))
        configured_switches = data.get("switches")
        if configured_switches is not None:
            self.switches = [
                {
                    "id": str(item.get("id", f"SW-{index:02d}")),
                    "position": float(item["position"]),
                    "lane_pairs": [tuple(map(int, pair)) for pair in item.get(
                        "lane_pairs", ((lane, lane + 1) for lane in range(len(self.lanes) - 1))
                    )],
                }
                for index, item in enumerate(configured_switches, start=1)
            ]
        else:
            spacing = max(300.0, float(data.get("switch_spacing_m", 1500.0)))
            first = max(100.0, float(data.get("first_switch_m", 900.0)))
            positions = list(self._positions(first, spacing, line.path.total_length))
            if data.get("station_switches", False):
                interval = max(1, int(data.get("station_switch_interval", 4)))
                approach = max(self.switch_length, float(
                    data.get("switch_offset_from_station_m", 260.0)
                ))
                for station_index, station in enumerate(getattr(line, "stations", [])):
                    if station_index % interval == 0:
                        center = float(station.get("position", 0.0))
                        positions.extend((center - approach, center + approach))
            positions = sorted({
                round(position, 2) for position in positions
                if self.switch_length / 2 <= position <= line.path.total_length - self.switch_length / 2
            })
            pairs = [(lane, lane + 1) for lane in range(len(self.lanes) - 1)]
            self.switches = [
                {"id": f"SW-{index:02d}", "position": position, "lane_pairs": pairs}
                for index, position in enumerate(positions, start=1)
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
        if "offset_m" in lane:
            return float(lane["offset_m"])
        return float(lane.get("offset_px", 0.0)) / 28.0

    def lane_offset(self, train, position=None):
        change = getattr(train, "track_change", None)
        if not change:
            return self.lane_offset_for_index(train.track_index)
        position = float(train.position if position is None else position)
        span = max(0.001, change["end"] - change["start"])
        progress = ((position - change["start"]) / span if change.get("direction", 1) > 0
                    else (change["end"] - position) / span)
        blend = self._smoothstep(progress)
        start = self.lane_offset_for_index(change["from"])
        end = self.lane_offset_for_index(change["to"])
        return start + (end - start) * blend

    def tint_for_train(self, train, position=None):
        change = getattr(train, "track_change", None)
        lane_index = train.track_index
        if change:
            position = float(train.position if position is None else position)
            span = max(0.001, change["end"] - change["start"])
            progress = ((position - change["start"]) / span if change.get("direction", 1) > 0
                        else (change["end"] - position) / span)
            if self._smoothstep(progress) >= 0.5:
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
        train_direction = -1 if int(getattr(train, "direction", 1)) < 0 else 1
        lane_direction = int(self.lanes[target].get("direction", train_direction))
        if lane_direction not in (0, train_direction):
            self.last_message = "Этот путь предназначен для встречного движения"
            return False
        available = [
            switch for switch in self.switches
            if (source, target) in switch.get("lane_pairs", [])
            and self.switch_length / 2 <=
                (switch["position"] - float(train.position)) * train_direction
                <= self.switch_window
        ]
        if not available:
            self.last_message = "Рядом нет стрелочного перевода для этих путей"
            return False
        switch = min(available, key=lambda item: abs(item["position"] - train.position))
        half = self.switch_length / 2
        start = switch["position"] - half
        end = switch["position"] + half
        zone_start = start - self.switch_length / 2
        zone_end = end + self.switch_length / 2
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
        if train_direction > 0:
            transition_start, transition_end = max(float(train.position), start), end
        else:
            transition_start, transition_end = start, min(float(train.position), end)
        if transition_end - transition_start <= 0.001:
            self.last_message = "Стрелочный перевод уже пройден"
            return False
        train.track_change = {
            "from": source, "to": target,
            "start": transition_start, "end": transition_end,
            "direction": train_direction, "switch": switch["id"],
        }
        self.last_message = f"Перевод на {self.lanes[target].get('label', 'путь')}"
        return True

    def update_train(self, train):
        change = getattr(train, "track_change", None)
        if not change:
            return
        length = float(getattr(train, "consist_length_m", 0.0))
        if change.get("direction", 1) > 0:
            tail_position = float(train.position) - length
            cleared = tail_position >= change["end"]
        else:
            tail_position = float(train.position) + length
            cleared = tail_position <= change["start"]
        if cleared:
            train.track_index = change["to"]
            train.track_change = None
            self.last_message = f"Занят {self.lanes[train.track_index].get('label', 'путь')}"
