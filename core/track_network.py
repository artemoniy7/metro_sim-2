"""Parallel-track layout with world-space offsets and safe crossovers."""
class TrackNetwork:
    def __init__(self, line, data=None, local_layout=None):
        data = data or {}
        self.line = line
        self.main_lane = int(data.get("main_lane", 1))
        # Default layout has exactly two parallel tracks. Lines with a
        # dedicated track file can provide their own labels and directions.
        self.lanes = list(data.get("lanes", [
            {"id": "opposing", "label": "Встречный путь", "offset_m": -3.43},
            {"id": "main", "label": "Главный путь", "offset_m": 0.0},
        ]))
        if not self.lanes:
            self.lanes = [{"id": "main", "label": "Главный путь", "offset_m": 0.0}]
        self.main_lane = max(0, min(len(self.lanes) - 1, self.main_lane))
        self.switch_length = max(40.0, float(data.get("switch_length_m", 100.0)))
        self.switch_window = max(self.switch_length, float(data.get("switch_window_m", 120.0)))
        spacing = max(300.0, float(data.get("switch_spacing_m", 1500.0)))
        first = max(100.0, float(data.get("first_switch_m", 900.0)))
        positions = list(self._positions(first, spacing, line.path.total_length))
        # Add paired crossovers outside selected station platforms. This makes
        # the route changes visible near stations without putting points under platforms.
        if data.get("station_switches", False):
            interval = max(1, int(data.get("station_switch_interval", 4)))
            approach = max(self.switch_length, float(
                data.get("switch_offset_from_station_m", 260.0)
            ))
            for station_index, station in enumerate(getattr(line, "stations", [])):
                if station_index % interval != 0:
                    continue
                # Skip the entire crossover pair at configured stations.
                if station.get("name") in set(data.get("station_switches_skip", [])):
                    continue
                center = float(station.get("position", 0.0))
                positions.extend((center - approach, center + approach))
        positions = sorted({
            round(position, 2) for position in positions
            if self.switch_length / 2 <= position <= line.path.total_length - self.switch_length / 2
        })
        self.switches = [
            {"id": f"SW-{index:02d}", "position": position}
            for index, position in enumerate(positions, start=1)
        ]
        # Optional station/dead-end geometry is kept in a separate file so the
        # line-wide parallel-track configuration remains unchanged.
        local_layout = local_layout or {}
        self.local_track_segments = list(local_layout.get("track_segments", []))
        self.local_switches = list(local_layout.get("switches", []))
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
            override = getattr(train, "track_offset_override_m", None)
            return (float(override) if override is not None
                    else self.lane_offset_for_index(train.track_index))
        position = float(train.position if position is None else position)
        span = max(0.001, abs(change["end"] - change["start"]))
        blend = self._smoothstep(
            (position - change["start"]) / (change["end"] - change["start"])
        )
        start = float(change.get("from_offset_m", self.lane_offset_for_index(change["from"])))
        end = float(change.get("to_offset_m", self.lane_offset_for_index(change["to"])))
        return start + (end - start) * blend

    def tint_for_train(self, train, position=None):
        change = getattr(train, "track_change", None)
        lane_index = train.track_index
        if change:
            position = float(train.position if position is None else position)
            blend = self._smoothstep(
                (position - change["start"]) / (change["end"] - change["start"])
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
                    f"{change.get('to_label', self.lanes[change['to']].get('label', 'Путь'))}")
        override_label = getattr(train, "track_offset_label", None)
        if override_label:
            return str(override_label)
        return str(self.lanes[train.track_index].get("label", "Путь"))

    @staticmethod
    def _junction_train_positions(train, direction):
        """Return the leading and trailing outer wheel positions of the whole consist.

        ``train.position`` is anchored at the index-0 cab, not at the consist
        centre. The rendered consist extends one locomotive length in the
        increasing-coordinate direction and the remaining consist length in
        the decreasing-coordinate direction. Use those two physical ends so
        junction locking follows the first and last wheelsets, including when
        the train reverses.
        """
        direction = 1 if int(direction) >= 0 else -1
        anchor = float(train.position)
        loco_length = max(0.0, float(getattr(train, "loco_length_m", 0.0)))
        consist_length = max(
            loco_length, float(getattr(train, "consist_length_m", loco_length))
        )
        low_end = anchor - (consist_length - loco_length)
        high_end = anchor + loco_length
        if direction > 0:
            return high_end, low_end
        return low_end, high_end

    @staticmethod
    def _junction_state_occupied(state, first_end, second_end):
        """Return whether any part of the consist overlaps the junction zone.

        Occupancy is deliberately independent of travel direction: a train
        may stop or reverse while its consist is inside the turnout.
        """
        zone_start = min(float(state["entry"]), float(state["exit"]))
        zone_end = max(float(state["entry"]), float(state["exit"]))
        consist_start = min(float(first_end), float(second_end))
        consist_end = max(float(first_end), float(second_end))
        return consist_end >= zone_start and consist_start <= zone_end

    def request_lane_change(self, train, direction, trains):
        """Track switching is intentionally disabled during the junction rewrite.

        Track geometry, route metadata and renderer inputs remain available;
        only movement between tracks is disabled.
        """
        self.last_message = "Переключение путей временно отключено"
        return False
