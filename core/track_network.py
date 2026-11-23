"""Parallel-track layout with entry/exit based local junction routing."""
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
        # Do not synthesize crossovers along the route or beside stations.
        # Only draw switches explicitly supplied by a track-layout file.
        self.switches = [dict(switch) for switch in data.get("switches", [])]
        # Optional station/dead-end geometry is kept in a separate file so the
        # line-wide parallel-track configuration remains unchanged.
        local_layout = local_layout or {}
        self.local_track_segments = list(local_layout.get("track_segments", []))
        self.local_switches = list(local_layout.get("switches", []))
        self.junctions = TrackJunctionSystem(self.local_switches)
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

    def station_lane_offset_m(self, offset_m, position):
        """Keep each track's own offset; the station shell shifts the pair as a unit.

        The two tracks must stay parallel and physically separate through the
        station. Their shared centre is aligned by station_shell_y_at() in the
        renderer; collapsing each lane onto the midpoint would draw one track.
        """
        return float(offset_m)

    def station_platform_lane_indices(self, station):
        """Return the tracks adjacent to the station platforms in this layout."""
        configured = station.get("platform_lane_indices")
        if configured is not None:
            indices = []
            for value in configured:
                try:
                    index = int(value)
                except (TypeError, ValueError):
                    continue
                if 0 <= index < len(self.lanes) and index not in indices:
                    indices.append(index)
            return indices or [self.main_lane]

        layout = str(station.get("platform_layout", "island")).lower()
        if layout in {"side", "outer"}:
            return list(range(len(self.lanes)))
        return [self.main_lane]

    def _track_change_blend(self, change, position):
        """Return the transition progress without dividing by a zero-length span."""
        start = float(change["start"])
        end = float(change["end"])
        span = end - start
        if abs(span) <= 1e-9:
            # A degenerate transition has no drawable interval; treat it as
            # complete so rendering remains deterministic and never crashes.
            return 1.0
        return self._smoothstep((float(position) - start) / span)

    def lane_offset(self, train, position=None):
        change = getattr(train, "track_change", None)
        if not change:
            override = getattr(train, "track_offset_override_m", None)
            return (float(override) if override is not None
                    else self.lane_offset_for_index(train.track_index))
        position = float(train.position if position is None else position)
        blend = self._track_change_blend(change, position)
        start = float(change.get("from_offset_m", self.lane_offset_for_index(change["from"])))
        end = float(change.get("to_offset_m", self.lane_offset_for_index(change["to"])))
        return start + (end - start) * blend

    def tint_for_train(self, train, position=None):
        change = getattr(train, "track_change", None)
        lane_index = train.track_index
        if change:
            position = float(train.position if position is None else position)
            blend = self._track_change_blend(change, position)
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
    def _train_edges(train):
        """Estimate consist ends from the cab-0 anchor; exact wheelsets are not modeled."""
        anchor = float(train.position)
        loco = max(0.0, float(getattr(train, "loco_length_m", 0.0)))
        length = max(loco, float(getattr(train, "consist_length_m", loco)))
        low, high = anchor - max(0.0, length - loco), anchor + loco
        return (high, low) if int(getattr(train, "direction", 1)) >= 0 else (low, high)

    @staticmethod
    def _crossed(previous, current, point, direction):
        return previous is not None and (previous - point) * direction < 0 <= (current - point) * direction

    def _current_offset(self, train):
        active = getattr(train, "_junction_active_zones", [])
        if active:
            return float(active[-1]["to_offset_m"])
        override = getattr(train, "track_offset_override_m", None)
        return float(override) if override is not None else self.lane_offset_for_index(train.track_index)

    def request_route_selection(self, train, direction):
        leading, _ = self._train_edges(train)
        travel = 1 if int(getattr(train, "direction", 1)) >= 0 else -1
        routes = self.junctions.matching_routes(self._current_offset(train), travel)
        options = self.junctions.available_routes(routes, leading, travel, self.switch_window)
        if not options:
            self.last_message = "Впереди нет доступной стрелки"
            return False
        key = self.junctions.cursor_key(options[0])
        active = getattr(train, "_junction_active_zones", [])
        if any(zone["junction_key"] == key for zone in active):
            self.last_message = "Маршрут уже зафиксирован"
            return False
        selections = getattr(train, "_junction_route_selection", {})
        cursor = getattr(train, "_junction_route_cursor", {})
        selected = selections.get(key)
        if selected is not None:
            cursor[key] = self.junctions.route_index(options, selected)
        chosen = self.junctions.choose_route(options, direction, cursor)
        cursor[key] = self.junctions.route_index(options, chosen)
        selections[key] = chosen
        train._junction_route_selection = selections
        train._junction_route_cursor = cursor
        self.last_message = "Маршрут: " + str(chosen.get("to_label", chosen.get("id", "выбран")))
        return True

    def request_lane_change(self, train, direction, trains):
        """Compatibility wrapper for the former Q/E switching entry point."""
        return self.request_route_selection(train, direction)

    def update_train(self, train):
        """Lock the chosen route at entry and release its zone after the tail clears exit."""
        leading, trailing = self._train_edges(train)
        travel = 1 if int(getattr(train, "direction", 1)) >= 0 else -1
        if not self.local_switches:
            # A legacy or stale transition must not keep shifting a train when
            # this route has no explicitly configured junctions.
            train.track_change = None
            train._junction_active_zones = []
            train._junction_route_state = None
            train._junction_previous_edges = (leading, trailing)
            train._junction_previous_direction = travel
            return
        previous = getattr(train, "_junction_previous_edges", (None, None))
        prev_lead, prev_tail = previous
        previous_direction = getattr(train, "_junction_previous_direction", travel)
        direction_changed = previous_direction != travel
        active = list(getattr(train, "_junction_active_zones", []))
        selections = getattr(train, "_junction_route_selection", {})
        offset = self._current_offset(train)
        crossed = {}
        # Reversing swaps which end of the consist is leading. That change can
        # move the calculated leading edge across a turnout without the train
        # physically travelling over it. Only detect entry crossings while the
        # travel direction is unchanged.
        if not direction_changed:
            for route in self.junctions.matching_routes(offset, travel):
                entry = float(route.get("position_m", route.get("start_m", 0.0)))
                if self._crossed(prev_lead, leading, entry, travel):
                    crossed.setdefault(self.junctions.cursor_key(route), []).append(route)
        for key, group in crossed.items():
            if any(zone["junction_key"] == key for zone in active):
                continue
            group.sort(key=lambda route: (int(route.get("route_order", 0)), str(route.get("id", ""))))
            wanted = selections.pop(key, None)
            route = next((item for item in group if wanted and item.get("id") == wanted.get("id")), group[0])
            entry = float(route.get("position_m", route.get("start_m", 0.0)))
            exit_point = float(route.get("end_m", entry))
            zone = {
                "junction_key": key, "route_id": route.get("id"),
                "entry": entry, "exit": exit_point, "direction": travel,
                "from_offset_m": float(route.get("from_offset_m", offset)),
                "to_offset_m": float(route.get("to_offset_m", offset)),
                "to_label": route.get("to_label", route.get("id", "Путь")),
            }
            active.append(zone)
            train.track_change = {
                "from": train.track_index, "to": train.track_index,
                "start": entry, "end": exit_point,
                "from_offset_m": zone["from_offset_m"],
                "to_offset_m": zone["to_offset_m"],
                "to_label": zone["to_label"], "switch": zone["route_id"],
            }
        remaining = []
        cleared_offset = None
        for zone in active:
            if (not direction_changed
                    and self._crossed(prev_tail, trailing, zone["exit"], zone["direction"])):
                cleared_offset = zone["to_offset_m"]
                train.track_offset_label = zone["to_label"]
            else:
                remaining.append(zone)
        train._junction_active_zones = remaining
        if remaining:
            zone = remaining[-1]
            train.track_change = {
                "from": train.track_index, "to": train.track_index,
                "start": zone["entry"], "end": zone["exit"],
                "from_offset_m": zone["from_offset_m"],
                "to_offset_m": zone["to_offset_m"],
                "to_label": zone["to_label"], "switch": zone["route_id"],
            }
        elif cleared_offset is not None:
            train.track_change = None
            train.track_offset_override_m = cleared_offset
        train._junction_previous_edges = (leading, trailing)
        train._junction_previous_direction = travel
