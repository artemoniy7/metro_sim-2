"""Parallel-track layout with world-space offsets and safe crossovers."""
from core.track_junctions import TrackJunctionSystem
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
        self.junction_system = TrackJunctionSystem(self.local_switches)
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
        active_change = getattr(train, "track_change", None)
        pending = getattr(train, "_junction_route_state", None)
        train_direction = 1 if int(getattr(train, "direction", 1)) >= 0 else -1

        if pending:
            first_end, second_end = self._junction_train_positions(train, train_direction)
            occupied = self._junction_state_occupied(
                pending, first_end, second_end
            )
            if occupied:
                pending["locked"] = True
                self.last_message = "Стрелка занята — маршрут зафиксирован"
                return False
            if pending.get("locked") or train_direction != int(
                    pending.get("direction", train_direction)):
                # The whole consist has left the turnout, or reversed before
                # entering it. Do not keep a stale route reservation forever.
                train._junction_route_state = None
                pending = None
                active_change = None
                train.track_change = None

        if active_change and pending is None:
            train_direction = 1 if int(active_change.get(
                "direction", train_direction
            )) >= 0 else -1

        if pending:
            current_offset = float(pending["from_offset_m"])
            source_lane = int(pending["from"])
        elif active_change:
            current_offset = float(active_change.get(
                "from_offset_m", self.lane_offset(train)
            ))
            source_lane = int(active_change.get("from", train.track_index))
        else:
            current_offset = self.lane_offset(train)
            source_lane = int(train.track_index)

        local_window = max(self.switch_window, 200.0)
        matching_local = self.junction_system.matching_routes(
            current_offset=current_offset,
            train_direction=train_direction,
        )
        local_candidates = self.junction_system.available_routes(
            matching_local,
            position=float(train.position),
            train_direction=train_direction,
            window=local_window,
        )
        if local_candidates:
            cursor = getattr(train, "_junction_route_cursor", {})
            switch = self.junction_system.choose_route(
                local_candidates, direction, cursor
            )
            selected_index = self.junction_system.route_index(local_candidates, switch)
            cursor[self.junction_system.cursor_key(switch)] = selected_index
            train._junction_route_cursor = cursor

            # The straight-through route is a real third choice at the
            # turnout, but it needs no lateral transition: the main rails are
            # already rendered by the ordinary line renderer.
            # Treat the whole grouped junction as one physical zone. The
            # straight option has no lateral geometry of its own, so derive
            # the exit boundary from the connected crossover alternatives.
            entry = float(switch.get("position_m", switch.get("start_m", train.position)))
            spans = [
                (float(route.get("start_m", entry)), float(route.get("end_m", entry)))
                for route in local_candidates
                if abs(float(route.get("start_m", entry))
                       - float(route.get("end_m", entry))) > 0.01
            ]
            if spans:
                boundaries = [value for span in spans for value in span]
                exit_position = (min(boundaries) if train_direction < 0
                                 else max(boundaries))
            else:
                exit_position = entry

            if switch.get("route_type") == "straight":
                train.track_change = None
                train._junction_route_state = {
                    "junction_id": self.junction_system.cursor_key(switch),
                    "entry": entry, "exit": exit_position,
                    "direction": train_direction, "from": source_lane,
                    "from_offset_m": current_offset, "locked": False,
                }
                self.last_message = (
                    f"Маршрут: {switch.get('to_label', 'Главный путь')} "
                    f"({selected_index + 1}/{len(local_candidates)})"
                )
                return True

            start = float(switch["start_m"])
            end = float(switch["end_m"])
            if (end - start) * train_direction <= 0:
                self.last_message = "Стрелочный перевод уже пройден"
                return False
            target_offset = float(switch["to_offset_m"])
            target_lane = next((i for i in range(len(self.lanes))
                                if abs(self.lane_offset_for_index(i) - target_offset) < 0.15),
                               source_lane)
            train.track_change = {
                "from": source_lane, "to": target_lane,
                "from_offset_m": current_offset, "to_offset_m": target_offset,
                "start": start, "end": end, "switch": switch.get("id", "LOCAL"),
                "junction_id": switch.get("junction_id"),
                "to_label": switch.get("to_label", "Дополнительный путь"),
                "direction": train_direction,
            }
            train._junction_route_state = {
                "junction_id": self.junction_system.cursor_key(switch),
                "entry": entry, "exit": exit_position,
                "direction": train_direction, "from": source_lane,
                "from_offset_m": current_offset, "locked": False,
            }
            self.last_message = (
                f"Маршрут: {switch.get('to_label', 'дополнительный путь')} "
                f"({selected_index + 1}/{len(local_candidates)})"
            )
            return True

        # If a local connection exists for this track and direction but is
        # outside the selection window, report its distance instead of falling
        # through to the unrelated two-lane neighbour logic.
        if matching_local:
            distances = [
                (float(item.get("position_m", item.get("start_m", 0.0)))
                 - float(train.position)) * train_direction
                for item in matching_local
            ]
            ahead = [distance for distance in distances if distance >= 0.0]
            if ahead:
                self.last_message = f"Стрелка через {min(ahead):.0f} м"
            else:
                self.last_message = "Локальная стрелка уже пройдена"
            return False

        source = int(train.track_index)
        target = source + (1 if direction > 0 else -1)
        if target < 0 or target >= len(self.lanes):
            self.last_message = "Соседнего пути нет"
            return False
        train_direction = int(getattr(train, "direction", 1))
        lane_direction = int(self.lanes[target].get("direction", train_direction))
        if lane_direction != train_direction:
            self.last_message = "Этот путь предназначен для встречного движения"
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
        pending = getattr(train, "_junction_route_state", None)
        if pending:
            direction = 1 if int(getattr(train, "direction", 1)) >= 0 else -1
            first_end, second_end = self._junction_train_positions(train, direction)
            occupied = self._junction_state_occupied(
                pending, first_end, second_end
            )
            if occupied:
                pending["locked"] = True
            elif (pending.get("locked") or direction != int(
                    pending.get("direction", direction))):
                train._junction_route_state = None

        change = getattr(train, "track_change", None)
        if not change:
            return
        # Reserve both connected tracks until the tail of the consist clears.
        train_direction = int(change.get("direction", getattr(train, "direction", 1)))
        _, rear_position = self._junction_train_positions(train, train_direction)
        cleared = (rear_position >= change["end"] if train_direction >= 0
                   else rear_position <= change["end"])
        if cleared:
            target_offset = float(change.get("to_offset_m",
                                      self.lane_offset_for_index(change["to"])))
            train.track_index = change["to"]
            matching_lane = next((i for i in range(len(self.lanes))
                                  if abs(self.lane_offset_for_index(i) - target_offset) < 0.15), None)
            train.track_offset_override_m = (None if matching_lane is not None else target_offset)
            train.track_offset_label = (None if matching_lane is not None
                                        else change.get("to_label", "Центральный путь"))
            if matching_lane is not None:
                train.track_index = matching_lane
            train.track_change = None
            self.last_message = f"Занят {change.get('to_label', self.lanes[train.track_index].get('label', 'путь'))}"
