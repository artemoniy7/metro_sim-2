"""Reusable route selection for multi-way railway junctions.

A junction is described by directed route records in a line layout. Each route
keeps its own geometry (start_m/end_m and source/target offsets), while this
class handles discovery and selection independently of any particular line.
"""
from __future__ import annotations


class TrackJunctionSystem:
    """Find and select routes belonging to a shared track-junction node."""

    def __init__(self, routes=None):
        self.routes = [dict(route) for route in (routes or [])]

    @staticmethod
    def _junction_key(route):
        # Legacy layouts without junction_id remain compatible. Routes sharing
        # the same source, direction and entry coordinate form one junction.
        if route.get("junction_id") is not None:
            return str(route["junction_id"])
        return (
            round(float(route.get("from_offset_m", 0.0)), 3),
            int(route.get("travel_direction", 1)),
            round(float(route.get("position_m", route.get("start_m", 0.0))), 2),
        )

    def matching_routes(self, current_offset, train_direction, tolerance=0.15):
        """Return directed routes available from the train's current track."""
        return [
            route for route in self.routes
            if abs(float(route.get("from_offset_m", 0.0)) - current_offset) < tolerance
            and int(route.get("travel_direction", 1)) == train_direction
        ]

    def available_routes(self, routes, position, train_direction, window):
        """Return every option at the nearest reachable junction, in stable order."""
        reachable = []
        for route in routes:
            entry = float(route.get("position_m", route.get("start_m", 0.0)))
            distance = (entry - position) * train_direction
            if 0.0 <= distance <= window:
                reachable.append((distance, route))
        if not reachable:
            return []

        nearest_distance = min(distance for distance, _ in reachable)
        nearest = [
            route for distance, route in reachable
            if abs(distance - nearest_distance) < 0.01
        ]
        junction_key = self._junction_key(nearest[0])
        options = [
            route for _, route in reachable
            if self._junction_key(route) == junction_key
        ]
        return sorted(
            options,
            key=lambda route: (
                int(route.get("route_order", 0)),
                float(route.get("to_offset_m", 0.0)),
                str(route.get("id", "")),
            ),
        )

    @staticmethod
    def route_index(routes, selected):
        for index, route in enumerate(routes):
            if route is selected or route.get("id") == selected.get("id"):
                return index
        return 0

    def choose_route(self, routes, direction, cursor=None):
        """Move the route selector left/right through any number of options.

        First Q selects option 1 and first E option 2, preserving the familiar
        two-route behavior. Further Q/E presses cycle through all configured
        routes instead of silently limiting selection to two.
        """
        if not routes:
            return None
        cursor = cursor or {}
        key = self._junction_key(routes[0])
        previous = cursor.get(key)
        if previous is None:
            index = 0 if direction < 0 else min(1, len(routes) - 1)
        else:
            index = (int(previous) + (1 if direction > 0 else -1)) % len(routes)
        return routes[index]
