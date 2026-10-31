"""A metro line with passive signals and working station/block signals."""
from core.path import TrackPath
from core.signal import Signal


class Line:
    PASSIVE_SIGNAL_SPACING_M = 275.0

    def __init__(self, data=None):
        data = data or {}
        self.name = data.get("name", "Test line")
        self.color = tuple(data.get("color", [220, 45, 55]))
        self.path = TrackPath(data.get("points", [[0, 350], [500, 350], [1000, 350], [1600, 350]]))
        self.stations = sorted(data.get("stations", []), key=lambda item: float(item.get("position", 0)))
        self.signals = []
        self.traffic_trains = []
        self._create_signals()
        self.opposing_signals = self._create_opposing_signals()

    def _create_signals(self):
        """Passive conventional signals every ~275 m, plus working station signals."""
        total = self.path.total_length
        position = self.PASSIVE_SIGNAL_SPACING_M
        index = 1
        while position < total:
            # Do not place conventional signals within a station platform.
            on_platform = any(
                float(station.get("position", 0)) - float(station.get("length_m", 162)) / 2.0
                <= position <=
                float(station.get("position", 0)) + float(station.get("length_m", 162)) / 2.0
                for station in self.stations
            )
            if not on_platform:
                self.signals.append(Signal(
                    position=position, aspect="dark", name=f"П{index}",
                    operational=False, kind="passive", lamp_count=2,
                ))
            position += self.PASSIVE_SIGNAL_SPACING_M
            index += 1

        for index, station in enumerate(self.stations, start=1):
            center = float(station.get("position", 0))
            half_length = float(station.get("length_m", 162)) / 2.0
            entry_position = max(0.0, center - half_length - 50.0)
            exit_position = min(total, center + half_length + 50.0)
            self.signals.append(Signal(
                entry_position, "green", f"С{index}В",
                operational=True, kind="station_entry", lamp_count=2,
            ))
            self.signals.append(Signal(
                exit_position, "green", f"С{index}П",
                operational=True, kind="station_exit", lamp_count=3,
            ))

        # Safety cleanup: no signal head should stand within platform limits.
        self.signals = [
            signal for signal in self.signals
            if not any(
                float(station.get("position", 0)) - float(station.get("length_m", 162)) / 2.0
                <= signal.position <=
                float(station.get("position", 0)) + float(station.get("length_m", 162)) / 2.0
                for station in self.stations
            )
        ]
        self.signals.sort(key=lambda signal: signal.position)

    def _create_opposing_signals(self):
        """Build an independent, reverse-facing signal set for the opposing track."""
        opposing = []
        for signal in self.signals:
            position = signal.position
            if signal.kind in ("station_entry", "station_exit"):
                try:
                    station_index = int(signal.name[1:-1]) - 1
                    station = self.stations[station_index]
                except (ValueError, IndexError):
                    station = None
                if station is not None:
                    center = float(station.get("position", 0))
                    half_length = float(station.get("length_m", 162)) / 2.0
                    if signal.kind == "station_entry":
                        position = min(self.path.total_length, center + half_length + 50.0)
                    else:
                        position = max(0.0, center - half_length - 50.0)
            opposing.append(Signal(
                position=position, aspect=signal.aspect, name=signal.name,
                operational=signal.operational, kind=signal.kind,
                lamp_count=signal.lamp_count,
            ))
        opposing.sort(key=lambda signal: signal.position)
        return opposing

    def update_signals(self, train, train_speed=None, signals=None, direction=1):
        """Update signal aspects using a single, cached-per-frame block pass.

        Each physical signal bounds one block. A block stays occupied until
        the complete train consist has cleared its far boundary.
        """
        from bisect import bisect_left

        signal_set = self.signals if signals is None else signals
        direction = -1 if direction < 0 else 1
        trains = list(train) if isinstance(train, (list, tuple)) else [train]

        occupied_ranges = []
        for item in trains:
            if hasattr(item, "position"):
                leading = float(item.position)
                trailing = leading - direction * float(
                    getattr(item, "consist_length_m", 0.0)
                )
                occupied_ranges.append((min(leading, trailing), max(leading, trailing)))
            else:
                point = float(item)
                occupied_ranges.append((point, point))

        # Build physical block boundaries once, then evaluate each block once.
        positions = sorted({
            0.0,
            float(self.path.total_length),
            *(float(signal.position) for signal in signal_set
              if 0.0 <= float(signal.position) <= self.path.total_length),
        })
        if len(positions) < 2:
            for signal in signal_set:
                signal.set_aspect("dark" if not signal.operational else "green")
            return

        occupied = []
        for start, end in zip(positions, positions[1:]):
            occupied.append(any(
                high > start + 0.01 and low < end - 0.01
                for low, high in occupied_ranges
            ))

        # Consecutive clear-block counts are computed in linear time.
        clear_forward = [0] * len(occupied)
        clear_backward = [0] * len(occupied)
        run = 0
        for index in range(len(occupied) - 1, -1, -1):
            run = 0 if occupied[index] else run + 1
            clear_forward[index] = run
        run = 0
        for index in range(len(occupied)):
            run = 0 if occupied[index] else run + 1
            clear_backward[index] = run

        for signal in signal_set:
            if not signal.operational:
                signal.set_aspect("dark")
                continue

            signal_position = float(signal.position)
            boundary_index = bisect_left(positions, signal_position - 0.01)
            if direction > 0:
                block_index = boundary_index
                if block_index >= len(occupied):
                    signal.set_aspect("green")
                    continue
                current_occupied = occupied[block_index]
                free_blocks = clear_forward[block_index]
            else:
                block_index = boundary_index - 1
                if block_index < 0:
                    signal.set_aspect("green")
                    continue
                current_occupied = occupied[block_index]
                free_blocks = clear_backward[block_index]

            if current_occupied:
                signal.set_aspect("red")
            else:
                # Fewer than three clear blocks means a restrictive speed
                # indication (<70 km/h), represented by yellow.
                signal.set_aspect("yellow" if free_blocks < 3 else "green")

        # Station approach yellow is an additional restriction, but never
        # overrides a red aspect. This pass is limited to station-entry heads.
        entry_signals = [
            signal for signal in signal_set
            if signal.operational and signal.kind == "station_entry"
        ]
        if not entry_signals:
            return

        for item in trains:
            if not hasattr(item, "position"):
                continue
            leading = float(item.position)
            if direction > 0:
                station = next((
                    station for station in self.stations
                    if float(station.get("position", 0)) >= leading
                ), None)
                if station is None:
                    continue
                center = float(station.get("position", 0))
                half_length = float(station.get("length_m", 162)) / 2.0
                approaching = 0.0 <= center - half_length - leading <= 50.0
                if approaching:
                    for signal in entry_signals:
                        if signal.position >= leading and signal.aspect != "red":
                            signal.set_aspect("yellow")
            else:
                station = next((
                    station for station in reversed(self.stations)
                    if float(station.get("position", 0)) <= leading
                ), None)
                if station is None:
                    continue
                center = float(station.get("position", 0))
                half_length = float(station.get("length_m", 162)) / 2.0
                approaching = 0.0 <= leading - (center + half_length) <= 50.0
                if approaching:
                    for signal in entry_signals:
                        if signal.position <= leading and signal.aspect != "red":
                            signal.set_aspect("yellow")

    def block_indication(self, train_position, train=None):
        """Return an ALS-ARS code using the clear distance to the rear of trains ahead.

        A train occupies the block until its rear clears it. Therefore the
        following train gets a zero code while it is within one full block
        (275 m) of the preceding train's rear, not just its front reference.
        """
        # Treat the beginning of the line as the rear of a virtual queue:
        # all trains (including the player) are compared with trains ahead,
        # but the player can enter the line without being blocked by a bot
        # behind them. Position is the front reference; subtract the full
        # consist length to get the leading train's rear.
        clear_distances = []
        own_tracks = (set(getattr(train, "occupied_track_indices", {getattr(train, "track_index", 1)}))
                      if train is not None else None)
        for other in self.traffic_trains:
            if not hasattr(other, "position"):
                continue
            other_tracks = set(getattr(
                other, "occupied_track_indices", {getattr(other, "track_index", 1)}
            ))
            # Parallel tracks have independent blocks; a train in a crossover
            # occupies both connected tracks until its tail clears the switch.
            if own_tracks is not None and not own_tracks.intersection(other_tracks):
                continue
            other_position = float(other.position)
            if other_position <= float(train_position) + 1.0:
                continue
            other_length = float(getattr(other, "consist_length_m", 0.0))
            clear_distance = other_position - other_length - float(train_position)
            clear_distances.append(max(0.0, clear_distance))

        traffic_limit = 80
        traffic_blocks = 99
        if clear_distances:
            clear_gap = min(clear_distances)
            traffic_blocks = max(0, int(clear_gap // self.PASSIVE_SIGNAL_SPACING_M))
            # Delay each restriction by one block compared with the previous
            # profile, so braking does not start quite as early.
            if clear_gap <= 0:
                traffic_limit = 0
            elif clear_gap <= self.PASSIVE_SIGNAL_SPACING_M:
                traffic_limit = 40
            elif clear_gap <= 2 * self.PASSIVE_SIGNAL_SPACING_M:
                traffic_limit = 60
            elif clear_gap <= 3 * self.PASSIVE_SIGNAL_SPACING_M:
                traffic_limit = 70

        next_station = next((
            station for station in self.stations
            if float(station.get("position", 0)) >= train_position
        ), None)
        if next_station is not None:
            center = float(next_station.get("position", 0))
            half_length = float(next_station.get("length_m", 162)) / 2.0
            station_start = center - half_length
            station_end = center + half_length
            distance_to_platform = station_start - train_position

            if station_start <= train_position <= station_end:
                if train_position >= center:
                    return min(40, traffic_limit), min(1, traffic_blocks)
                return min(60, traffic_limit), min(1, traffic_blocks)
            if 0.0 <= distance_to_platform <= 50.0:
                return min(60, traffic_limit), min(1, traffic_blocks)
            if 50.0 < distance_to_platform <= 100.0:
                return min(70, traffic_limit), min(2, traffic_blocks)

        block_count = max(1, int(
            (self.path.total_length + self.PASSIVE_SIGNAL_SPACING_M - 1)
            // self.PASSIVE_SIGNAL_SPACING_M
        ))
        block_index = int(max(0.0, train_position) // self.PASSIVE_SIGNAL_SPACING_M)
        blocks_to_end = max(0, block_count - block_index - 1)
        if clear_distances:
            return traffic_limit, traffic_blocks
        if blocks_to_end >= 4:
            return 80, blocks_to_end
        if blocks_to_end == 3:
            return 70, blocks_to_end
        if blocks_to_end == 2:
            return 60, blocks_to_end
        if blocks_to_end == 1:
            return 40, blocks_to_end
        return 0, blocks_to_end
