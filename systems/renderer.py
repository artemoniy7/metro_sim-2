"""Side-on sprite renderer with per-model vehicle profiles."""
from pathlib import Path
import pygame
from settings import ASSETS_DIR
from core.train_models.oka import profile as oka_profile
from core.train_models.nomernoy import profile as nomernoy_profile
from core.train_models.rusich import profile as rusich_profile

TRAIN_RENDER_PROFILES = {
    "81-760": oka_profile,
    "81-717": nomernoy_profile,
    "81-740": rusich_profile,
}


class Renderer:
    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 21)
        self._train_model_id = None
        self.train_model_label = "81-760 Ока"
        self.door_animation_supported = True
        self.configure_train_model("81-760")
        self.door_open_amount = 0.0
        self.door_indicator_phase = 0.0
        self.tunnel_image = self._load_sprite(ASSETS_DIR / "track" / "tunnel.jpg")
        # Transparent signal sprite; lamp coordinates are in source-image pixels.
        self.signal_image = self._load_sprite(ASSETS_DIR / "track" / "light.png")
        self.signal_lamp_points = {
            # Lamp centers in the full 1024x1536 atlas.
            2: ((437, 101), (437, 190)),
            3: ((363, 451), (363, 585), (363, 724)),
        }
        self.signal_heads = {}
        if self.signal_image is not None:
            atlas_w, atlas_h = self.signal_image.get_size()
            signal_crops = {
                2: (385, 60, 90, 165),
                3: (315, 405, 95, 350),
            }
            for lamp_count, (cx, cy, cw, ch) in signal_crops.items():
                if cx + cw <= atlas_w and cy + ch <= atlas_h:
                    self.signal_heads[lamp_count] = self.signal_image.subsurface(
                        (cx, cy, cw, ch)
                    ).copy()
        self.signal_glow_cache = {}
        self.station_images = {}
        self.legacy_station_image = None
        self._station_asset_line_id = None
        self.vehicle_angles = {}
        self._station_tile_cache = {}
        self.last_render_time = None
        self._tunnel_tile_cache = {}
        self._opposing_tunnel_cache = {}
        self.cab_mirror = False
        self.main_lane_offset_m = 0.0
        self.lane_center_offset_m = 0.0

    def configure_train_model(self, train_or_model_id):
        """Load only the selected model's sprites; never borrow another model's art."""
        model_id = getattr(train_or_model_id, "model_id", train_or_model_id)
        model_id = str(model_id or "81-760")
        if model_id == self._train_model_id:
            return
        profile = TRAIN_RENDER_PROFILES.get(model_id)
        if profile is None:
            raise ValueError(f"No renderer profile registered for train model {model_id!r}")
        train_dir = ASSETS_DIR / "trains" / profile.ASSET_DIRECTORY
        self.loco_image = self._load_sprite(train_dir / profile.SPRITE_FILES["loco"])
        self.car_image = self._load_sprite(train_dir / profile.SPRITE_FILES["car"])
        self.door_left_image = self._load_sprite(train_dir / profile.SPRITE_FILES["door_left"])
        self.door_right_image = self._load_sprite(train_dir / profile.SPRITE_FILES["door_right"])
        self.door_animation_supported = bool(profile.DOOR_ANIMATION_SUPPORTED)
        self.train_model_label = f"{profile.TRAIN_MODEL_ID} {profile.DISPLAY_NAME}"
        self._train_model_id = model_id

    def configure_line_station_sprites(self, line_id):
        """Load station textures only from the selected line's asset folder."""
        line_id = str(line_id or "")
        if line_id == self._station_asset_line_id:
            return
        self._station_asset_line_id = line_id
        station_dir = ASSETS_DIR / "stations" / line_id
        self.station_images = {}
        self.legacy_station_image = self._load_sprite(station_dir / "altufyevo.png")
        for station_number in range(1, 100):
            texture = self._load_sprite(station_dir / f"st_{station_number:02d}.png")
            if texture is not None:
                self.station_images[station_number - 1] = texture
        self._station_tile_cache.clear()

    @staticmethod
    def _load_sprite(path):
        try:
            return pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, OSError):
            return None

    @staticmethod
    def _scaled_sprite(image, width, target_height=None):
        if image is None or image.get_width() <= 0:
            return None
        height = (max(1, round(width * image.get_height() / image.get_width()))
                  if target_height is None else max(1, int(target_height)))
        size = (max(1, width), height)
        cache = Renderer.__dict__.get("_sprite_scale_cache")
        if cache is None:
            cache = {}
            Renderer._sprite_scale_cache = cache
        key = (id(image), size)
        if key not in cache:
            cache[key] = pygame.transform.smoothscale(image, size)
            if len(cache) > 256:
                cache.clear()
                cache[key] = pygame.transform.smoothscale(image, size)
        return cache[key]

    def _draw_doors(self, sprite, source_image, vehicle_width, vehicle_height, is_loco, is_rear_cab=False):
        """Draw animated door leaves on passenger cars and both cab cars."""
        if (not self.door_animation_supported or self.door_left_image is None
                or self.door_right_image is None):
            return

        source_width, source_height = source_image.get_size()
        sx = vehicle_width / source_width
        sy = vehicle_height / source_height
        amount = self.door_open_amount

        if is_loco:
            # Door openings on the front cab sprite.
            openings = ((373, 81, 553, 322), (939, 81, 1119, 322),
                        (1433, 81, 1613, 322), (1897, 81, 2077, 322))
            if is_rear_cab:
                openings = tuple(
                    (source_width - x2, y1, source_width - x1, y2)
                    for x1, y1, x2, y2 in reversed(openings)
                )
            for x1, y1, x2, y2 in openings:
                door_height = max(1, round((y2 - y1) * sy))
                left_width = max(1, round(91 * sx))
                right_width = max(1, round(90 * sx))
                left_door = pygame.transform.smoothscale(
                    self.door_left_image, (left_width, door_height)
                )
                right_door = pygame.transform.smoothscale(
                    self.door_right_image, (right_width, door_height)
                )
                sprite.blit(left_door, (
                    round(x1 * sx - left_door.get_width() * amount),
                    round(y1 * sy)
                ))
                sprite.blit(right_door, (
                    round((x2 - 90) * sx + right_door.get_width() * amount),
                    round(y1 * sy)
                ))
        else:
            # Passenger-car door locations: upper and lower x coordinates
            # supplied for each opening. The two leaves slide apart from
            # the opening's upper/lower x positions as the doors open.
            top_xs = (171, 725, 1261, 1815)
            bottom_xs = (346, 900, 1436, 1990)
            if is_rear_cab:
                top_xs = tuple(source_width - x for x in reversed(bottom_xs))
                bottom_xs = tuple(source_width - x for x in reversed(top_xs))
            door_y = 70
            door_height = max(1, round((298 - door_y) * sy))
            left_width = max(1, round(90 * sx))
            right_width = max(1, round(90 * sx))
            left_door = pygame.transform.smoothscale(
                self.door_left_image, (left_width, door_height)
            )
            right_door = pygame.transform.smoothscale(
                self.door_right_image, (right_width, door_height)
            )
            for top_x, bottom_x in zip(top_xs, bottom_xs):
                sprite.blit(left_door, (
                    round(top_x * sx - left_door.get_width() * amount),
                    round(door_y * sy)
                ))
                sprite.blit(right_door, (
                    round((bottom_x - 90) * sx + right_door.get_width() * amount),
                    round(door_y * sy)
                ))

    def _draw_door_indicators(self, sprite, source_image, vehicle_width, vehicle_height,
                               is_loco, is_rear_cab, elapsed, active):
        if not active or not self.door_animation_supported:
            return
        # Half a second lit, half a second dark.
        if int(elapsed * 2.0) % 2 == 1:
            return
        source_width, source_height = source_image.get_size()
        sx = vehicle_width / source_width
        sy = vehicle_height / source_height
        points = ((463, 75), (1030, 75), (1525, 75), (1990, 75)) if is_loco else (
            (258, 65), (815, 65), (1349, 65), (1904, 65)
        )
        if is_rear_cab:
            points = tuple((source_width - x, y) for x, y in reversed(points))
        radius = max(2, round(7 * min(sx, sy)))
        for x, y in points:
            center = (round(x * sx), round(y * sy))
            pygame.draw.circle(sprite, (70, 0, 0), center, radius + max(1, radius // 3))
            pygame.draw.circle(sprite, (255, 25, 20), center, radius)
            pygame.draw.circle(sprite, (255, 150, 140), (
                center[0] - max(1, radius // 3), center[1] - max(1, radius // 3)
            ), max(1, radius // 3))

    @staticmethod
    def _track_offset(world_x):
        """Smooth, shallow test-track rises and dips, measured in world metres."""
        import math
        return (0.45 * math.sin(world_x / 85.0)
                + 0.18 * math.sin(world_x / 38.0 + 0.8))

    @staticmethod
    def _station_wall_top(track_y, station_height, bottom_extra, mirrored):
        """Place the station wall above or below the rails with the active cab."""
        if mirrored:
            return track_y - station_height + bottom_extra
        return track_y - bottom_extra

    def _lane_offset_pixels(self, lane, scale):
        # Track spacing is stored in metres, so every lane follows camera zoom.
        # Legacy offset_px values are converted using the old default scale
        # (10 px/m * zoom 2.8) to preserve the previous default composition.
        offset_m = lane.get("offset_m")
        if offset_m is None:
            offset_m = float(lane.get("offset_px", 0.0)) / 28.0
        mirror = -1.0 if self.cab_mirror else 1.0
        return (float(offset_m) - self.main_lane_offset_m) * scale * mirror

    def _draw_parallel_tracks(self, surface, line, camera_x, scale, rail_y_at, network):
        """Draw parallel paths with world-space spacing, behind the tunnel shell."""
        if network is None:
            return
        width = surface.get_width()
        spacing_m = 2.5
        first_world = camera_x
        last_world = camera_x + width / scale
        for lane_index, lane in enumerate(network.lanes):
            if lane_index == network.main_lane:
                continue
            offset = self._lane_offset_pixels(lane, scale)
            rail_top = tuple(lane.get("rail_top", (145, 151, 160)))
            rail_side = tuple(lane.get("rail_side", (76, 83, 93)))
            sleeper_color = tuple(lane.get("sleeper", (88, 83, 76)))
            ballast = tuple(lane.get("ballast", (39, 43, 51)))
            previous = None            for sx in range(0, width, 4):
                sy = rail_y_at(sx) + offset
                if previous is not None:
                    px, py = previous
                    pygame.draw.polygon(surface, ballast, [
                        (px, py + 8), (sx, sy + 8),
                        (sx, sy + 24), (px, py + 24)
                    ])
                previous = (sx, sy)
            sleeper = int(first_world / spacing_m) * spacing_m
            while sleeper < last_world:
                sx = round((sleeper - camera_x) * scale)
                if 0 <= sx < width:
                    sy = rail_y_at(sx) + offset
                    pygame.draw.line(surface, sleeper_color, (sx, sy - 1),
                                     (sx, sy + 14), 3)
                sleeper += spacing_m
            for sx in range(0, width, 4):
                ex = min(width, sx + 4)
                y1 = rail_y_at(sx) + offset
                y2 = rail_y_at(min(width - 1, ex)) + offset
                pygame.draw.line(surface, rail_top, (sx, y1 + 1), (ex, y2 + 1), 4)
                pygame.draw.line(surface, rail_side, (sx, y1 + 7), (ex, y2 + 7), 2)

        # Smooth connectors between adjacent paths; all remain on one plane.
        for switch in network.switches:
            start = max(0.0, switch["position"] - network.switch_length / 2)
            end = min(line.path.total_length, switch["position"] + network.switch_length / 2)
            if end <= start:
                continue
            for lane_a in range(len(network.lanes) - 1):
                lane_b = lane_a + 1
                rail_one, rail_two = [], []
                for step in range(17):
                    t = step / 16
                    eased = t * t * (3.0 - 2.0 * t)
                    route_position = start + (end - start) * t
                    sx = round((line.path.total_length - route_position - camera_x) * scale)
                    if sx < -20 or sx > width + 20:
                        continue
                    base_y = rail_y_at(max(0, min(width - 1, sx)))
                    offset_a = self._lane_offset_pixels(network.lanes[lane_a], scale)
                    offset_b = self._lane_offset_pixels(network.lanes[lane_b], scale)
                    y = base_y + offset_a + (offset_b - offset_a) * eased
                    rail_one.append((sx, round(y + 1)))
                    rail_two.append((sx, round(y + 7)))
                if len(rail_one) > 1:
                    pygame.draw.lines(surface, (156, 162, 170), False, rail_one, 4)
                    pygame.draw.lines(surface, (83, 90, 99), False, rail_two, 2)

    @staticmethod
    def _train_track_offset(network, train, wagon_position):
        # TrackNetwork returns metres; convert with the same camera scale as rails.
        return network.lane_offset(train, wagon_position) if network is not None else 0.0

    @staticmethod
    def _dim_train_sprite(sprite):
        # Trains on a different track are shown in shadow, without recolouring
        # the player's own train or changing its appearance during a crossover.
        sprite.fill((145, 150, 160, 255), special_flags=pygame.BLEND_RGBA_MULT)

    def _draw_signal(self, surface, signal, x, track_y, tunnel_height, scale, alpha=255):
        """Draw a zoom-aware signal centered vertically inside its tunnel."""
        zoom = max(0.35, scale / 28.0)
        head_width = max(8, round(18 * zoom))
        head_height = max(18, round(40 * zoom))
        lamp_radius = max(2, round(5 * zoom))
        font = pygame.font.Font(None, max(12, round(21 * zoom)))
        label = font.render(signal.name, True, (205, 210, 218)) if signal.operational else None
        margin_x = max(5, round(12 * zoom))
        margin_y = max(5, font.get_height() + round(5 * zoom))
        label_width = label.get_width() if label is not None else 0
        layer_width = margin_x * 2 + head_width + (label_width + round(8 * zoom) if label else 0)
        layer_height = margin_y * 2 + head_height
        layer = pygame.Surface((max(1, layer_width), max(1, layer_height)), pygame.SRCALPHA)
        head_x = margin_x
        head_y = margin_y
        center_x = head_x + head_width // 2
        pole_color = (88, 91, 98) if signal.operational else (65, 67, 72)
        bracket_y = head_y + head_height // 2
        pygame.draw.line(
            layer, (*pole_color, 255),
            (max(0, head_x - round(7 * zoom)), bracket_y),
            (head_x, bracket_y), max(1, round(3 * zoom))
        )
        body = pygame.Rect(head_x, head_y, head_width, head_height)
        pygame.draw.rect(layer, (20, 22, 26, 255), body, border_radius=max(1, round(3 * zoom)))
        pygame.draw.rect(layer, (*pole_color, 255), body, max(1, round(zoom)), border_radius=max(1, round(3 * zoom)))

        lamp_aspects = ("red", "green") if signal.lamp_count == 2 else ("red", "yellow", "green")
        for lamp_index, aspect in enumerate(lamp_aspects):
            lamp_y = head_y + round((lamp_index + 0.5) * head_height / len(lamp_aspects))
            if signal.operational and signal.aspect == aspect:
                color = signal.ASPECTS[aspect]
                pygame.draw.circle(layer, (*color, 255), (center_x, lamp_y), lamp_radius)
                pygame.draw.circle(layer, (255, 245, 225, 255), (
                    center_x - max(1, lamp_radius // 3), lamp_y - max(1, lamp_radius // 3)
                ), max(1, round(2 * zoom)))
            else:
                pygame.draw.circle(layer, (45, 47, 51, 255), (center_x, lamp_y), lamp_radius)

        if label is not None:
            layer.blit(label, (head_x + head_width + round(4 * zoom), head_y - font.get_height() - round(2 * zoom)))

        if alpha < 255:
            layer.set_alpha(max(0, min(255, int(alpha))))
        top = round(track_y - tunnel_height / 2 - head_height / 2 - margin_y)
        surface.blit(layer, (round(x - center_x), top))

    def draw_scene(self, surface, line, train, camera, elapsed, doors_open=False, door_closing=False, other_trains=None, station_simulation=None, depot_mode=False, depot_route_set=False, track_network=None):
        width, height = surface.get_size()
        if self.last_render_time is None:
            frame_dt = 1.0 / 60.0
        else:
            frame_dt = max(0.0, min(0.1, elapsed - self.last_render_time))
        self.last_render_time = elapsed
        target_door_amount = 1.0 if doors_open else 0.0
        door_step = frame_dt / 4.0
        if self.door_open_amount < target_door_amount:
            self.door_open_amount = min(target_door_amount, self.door_open_amount + door_step)
        elif self.door_open_amount > target_door_amount:
            self.door_open_amount = max(target_door_amount, self.door_open_amount - door_step)
        scale = camera.pixels_per_metre
        base_track_y = int(height * 0.79 - camera.panel_vertical_offset)
        camera_x = camera.x
        self.cab_mirror = bool(getattr(camera, "cab_swapped", False))
        if track_network is not None and track_network.lanes:
            offsets = [track_network.lane_offset_for_index(i)
                       for i in range(len(track_network.lanes))]
            self.main_lane_offset_m = offsets[track_network.main_lane]
            self.lane_center_offset_m = sum(offsets) / len(offsets)
        else:
            self.main_lane_offset_m = 0.0
            self.lane_center_offset_m = 0.0

        def rail_y_at(screen_x):
            world_x = camera_x + screen_x / scale
            route_position = max(0.0, min(line.path.total_length, line.path.total_length - world_x))
            path_depth = line.path.point_at(route_position)[1]
            depth_m = path_depth
            offset_weight = 1.0

            # Platforms are level, but their elevation must blend into the
            # tunnel gradually. Otherwise the procedural track offset and the
            # route profile create a visible kink right at the station exit.
            transition_m = 180.0
            for item in line.stations:
                center = float(item.get("position", 0))
                half_length = float(item.get("length_m", 162)) / 2.0
                distance = abs(route_position - center)
                station_depth = float(item.get("depth_m", path_depth))
                if distance <= half_length:
                    depth_m = station_depth
                    offset_weight = 0.0
                    break
                if distance < half_length + transition_m:
                    t = (distance - half_length) / transition_m
                    blend = t * t * (3.0 - 2.0 * t)
                    depth_m = station_depth * (1.0 - blend) + path_depth * blend
                    offset_weight = blend
                    break

            profile_scale = scale * (1.35 / 28.0)
            cab_sign = -1.0 if self.cab_mirror else 1.0
            return round(base_track_y + (depth_m - 10.0) * profile_scale
                         - self._track_offset(world_x) * scale * offset_weight
                         + cab_sign * (self.main_lane_offset_m - self.lane_center_offset_m) * scale)

        depot_length = float(getattr(line, "depot_length", 0.0))
        ground_y = int(height * 0.58 - camera.panel_vertical_offset)
        pygame.draw.rect(surface, (25, 30, 39), (0, 0, width, height))
        if depot_length > 0.0:
            # Surface depot scenery is drawn in world coordinates; it scrolls
            # under the exact same camera as the tunnel and station platforms.
            pygame.draw.rect(surface, (112, 164, 194), (0, 0, width, ground_y))
            pygame.draw.rect(surface, (79, 101, 70), (0, ground_y, width, height - ground_y))
            for tree_world in range(35, int(depot_length), 55):
                sx = round((line.path.total_length - tree_world - camera_x) * scale)
                if -60 < sx < width + 60:
                    pygame.draw.rect(surface, (79, 74, 58), (sx - 4, ground_y - 42, 8, 42))
                    pygame.draw.circle(surface, (58, 99, 68), (sx, ground_y - 52), 25)
            shed_world = 95.0
            shed_x = round((line.path.total_length - shed_world - camera_x) * scale)
            shed_w = round(125.0 * scale)
            if -shed_w < shed_x < width:
                pygame.draw.rect(surface, (137, 151, 157),
                                 (shed_x, ground_y - 125, shed_w, 125))
                pygame.draw.rect(surface, (65, 79, 88),
                                 (shed_x, ground_y - 125, shed_w, 125), 3)
                pygame.draw.rect(surface, (43, 53, 61),
                                 (shed_x + 12, ground_y - 83, shed_w - 24, 83))
        # Foreground ground is a backdrop: paint it before the tunnel and both tracks.
        for sx in range(0, width, 4):
            ex = min(width, sx + 4)
            y1, y2 = rail_y_at(sx), rail_y_at(min(width - 1, ex))
            pygame.draw.polygon(surface, (48, 51, 58), [(sx, y1 + 8), (ex, y2 + 8), (ex, height), (sx, height)])

        # Draw the lower opposing path over the tunnel backdrop, but keep it
        # inside the enlarged tunnel envelope. The main path is drawn last.

        # Texture resolution changes in small discrete steps instead of every
        # fractional camera-zoom update. This avoids visible resampling shimmer
        # while the control-panel camera animation is running.
        tunnel_height = max(4, round((5.5 * scale) / 4.0) * 4)
        # The main tunnel belongs only to the main track. The opposing track
        # gets its own foreground tunnel overlay after the trains are drawn.
        tunnel_draw_height = tunnel_height
        # train.position is anchored to cab 1's physical end. When cab 2 is
        # selected, its station position is one consist length behind that
        # reference; use the active cab to identify the occupied station.
        player_station_position = float(train.position)
        if self.cab_mirror:
            player_station_position -= max(
                0.0, float(train.consist_length_m) - float(train.loco_length_m)
            )
        player_station_index = next((
            index for index, station in enumerate(line.stations)
            if abs(player_station_position - float(station.get("position", 0.0)))
            <= float(station.get("length_m", 162)) / 2
        ), None)
        if self.tunnel_image is not None:
            tunnel_width = max(1, round(tunnel_draw_height * self.tunnel_image.get_width() / self.tunnel_image.get_height()))
            tunnel_key = (id(self.tunnel_image), tunnel_width, tunnel_draw_height)
            if tunnel_key not in self._tunnel_tile_cache:
                self._tunnel_tile_cache[tunnel_key] = pygame.transform.smoothscale(
                    self.tunnel_image, (tunnel_width, tunnel_draw_height)
                )
                if len(self._tunnel_tile_cache) > 48:
                    self._tunnel_tile_cache.pop(next(iter(self._tunnel_tile_cache)))
            tunnel_tile = self._tunnel_tile_cache[tunnel_key]
            strip_width = 4
            for sx in range(0, width, strip_width):
                world_x = camera_x + sx / scale
                route_position = line.path.total_length - world_x
                track_y = rail_y_at(sx)
                station_index = next((
                    index for index, station in enumerate(line.stations)
                    if abs(route_position - float(station.get("position", 0)))
                    <= float(station.get("length_m", 162)) / 2
                ), None)
                if depot_length > 0.0 and route_position < depot_length:
                    pygame.draw.rect(surface, (112, 164, 194), (sx, 0, strip_width, ground_y))
                    pygame.draw.rect(surface, (79, 101, 70),
                                     (sx, ground_y, strip_width, max(1, track_y - ground_y)))
                    pygame.draw.rect(surface, (70, 64, 56),
                                     (sx, track_y - 4, strip_width, 18))
                elif station_index is not None:
                    station_height = max(4, round((8.5 * scale) / 4.0) * 4)
                    station_bottom_extra = max(1, round(0.25 * scale))
                    station_wall_top = self._station_wall_top(
                        track_y, station_height, station_bottom_extra, self.cab_mirror
                    )
                    # At the station occupied by the train, show the adjacent
                    # station wall in the direction of the newly selected cab.
                    wall_station_index = station_index
                    if station_index == player_station_index:
                        adjacent_index = station_index + (-1 if self.cab_mirror else 1)
                        if 0 <= adjacent_index < len(line.stations):                            wall_station_index = adjacent_index
                    station_texture = self.station_images.get(
                        wall_station_index, self.legacy_station_image
                    )
                    if station_texture is not None:
                        station_width = max(1, round(
                            station_height * station_texture.get_width()
                            / station_texture.get_height()
                        ))
                        station_key = (id(station_texture), station_width, station_height)
                        if station_key not in self._station_tile_cache:
                            self._station_tile_cache[station_key] = pygame.transform.smoothscale(
                                station_texture, (station_width, station_height)
                            )
                            if len(self._station_tile_cache) > 128:
                                self._station_tile_cache.pop(next(iter(self._station_tile_cache)))
                        station_tile = self._station_tile_cache[station_key]
                        tile_world_width = station_width / scale
                        tile_x = int(((world_x % tile_world_width) / tile_world_width) * station_width)
                        src_x = min(station_width - 1, max(0, tile_x))
                        slice_width = min(strip_width, station_width - src_x)
                        if slice_width > 0:
                            station_slice = station_tile.subsurface(
                                (src_x, 0, slice_width, station_height)
                            )
                            surface.blit(
                                station_slice,
                                (sx, station_wall_top)
                            )
                        if slice_width < strip_width:
                            extra_width = min(strip_width - slice_width, station_width)
                            station_slice = station_tile.subsurface(
                                (0, 0, extra_width, station_height)
                            )
                            surface.blit(
                                station_slice,
                                (sx + slice_width, station_wall_top)
                            )
                    else:
                        pygame.draw.rect(
                            surface, (142, 24, 34),
                            (sx, station_wall_top, strip_width, station_height + 20)
                        )
                else:
                    src_x = int((world_x * scale) % tunnel_width)
                    src_x = min(tunnel_width - 1, max(0, src_x))
                    slice_width = min(strip_width, tunnel_width - src_x)
                    if slice_width > 0:
                        surface.blit(tunnel_tile.subsurface((src_x, 0, slice_width, tunnel_draw_height)), (sx, track_y - tunnel_height))
                        if slice_width < strip_width:
                            extra_width = min(strip_width - slice_width, tunnel_width)
                            surface.blit(tunnel_tile.subsurface((0, 0, extra_width, tunnel_draw_height)), (sx + slice_width, track_y - tunnel_height))
        else:
            for sx in range(0, width, 4):
                route_position = line.path.total_length - (camera_x + sx / scale)
                if depot_length > 0.0 and route_position < depot_length:
                    track_y = rail_y_at(sx)
                    pygame.draw.rect(surface, (112, 164, 194), (sx, 0, 4, ground_y))
                    pygame.draw.rect(surface, (79, 101, 70), (sx, ground_y, 4, max(1, track_y-ground_y)))
                elif any(abs(route_position - float(station.get("position", 0))) <= float(station.get("length_m", 155)) / 2 for station in line.stations):
                    track_y = rail_y_at(sx)
                    station_wall_top = self._station_wall_top(
                        track_y, tunnel_height, 0, self.cab_mirror
                    )
                    pygame.draw.rect(
                        surface, (142, 24, 34),
                        (sx, station_wall_top, 4, tunnel_height + 20)
                    )

        self._draw_parallel_tracks(surface, line, camera_x, scale, rail_y_at, track_network)

        sleeper_spacing = 2.5
        sleeper = int(camera_x / sleeper_spacing) * sleeper_spacing
        while sleeper < camera_x + width / scale:
            sx = int((sleeper - camera_x) * scale)
            if 0 <= sx < width:
                sy = rail_y_at(sx)
                pygame.draw.line(surface, (95, 89, 80), (sx, sy - 1), (sx, sy + 14), 3)
            sleeper += sleeper_spacing

        for sx in range(0, width, 4):
            ex = min(width, sx + 4)
            y1, y2 = rail_y_at(sx), rail_y_at(min(width - 1, ex))
            pygame.draw.line(surface, (155, 160, 167), (sx, y1 + 1), (ex, y2 + 1), 4)
            pygame.draw.line(surface, (85, 90, 98), (sx, y1 + 7), (ex, y2 + 7), 2)

        for station in line.stations:
            x = int((line.path.total_length - float(station.get("position", 0)) - camera_x) * scale)
            if -160 < x < width + 160:
                sy = rail_y_at(max(0, min(width - 1, x)))
                half_platform = int(float(station.get("length_m", 155)) * scale / 2)
                pygame.draw.line(surface, (205, 55, 65), (x - half_platform, sy - 8), (x + half_platform, sy - 8), 5)
                label = self.small_font.render(station.get("name", "Station"), True, (230, 234, 240))
                surface.blit(label, (x - label.get_width() // 2, sy - 43))
                distance = float(station.get("position", 0)) - train.position
                if distance > 0:
                    dlabel = self.small_font.render(f"{distance:.0f} m", True, (170, 190, 205))
                    surface.blit(dlabel, (x - dlabel.get_width() // 2, sy - 25))

        # Main-line signals scale with world zoom and sit at tunnel mid-height.
        for signal in line.signals:
            x = int((line.path.total_length - signal.position - camera_x) * scale)
            if -80 < x < width + 80:
                sy = rail_y_at(max(0, min(width - 1, x)))
                self._draw_signal(surface, signal, x, sy, tunnel_height, scale)

        loco_x = (line.path.total_length - train.position - train.loco_length_m - camera_x) * scale
        loco_width = max(1, round(train.loco_length_m * scale))
        car_width = max(1, round(train.car_length_m * scale))
        # Build the consist width from the same rounded sprite widths used
        # below. Rounding the metre total separately creates a small gap or
        # overlap between the cars and the rear locomotive after cab reversal.
        consist_width = (
            loco_width * 2 + max(0, len(train.wagons) - 2) * car_width
        )
        loco_scaled = self._scaled_sprite(self.loco_image, loco_width)
        loco_height = loco_scaled.get_height() if loco_scaled is not None else 48
        # The active cab determines which physical end leads the consist.
        # Reversing the reverser changes travel direction, not wagon order.
        reverse_player = getattr(train, "active_cab", 0) == 1
        player_wagons = reversed(train.wagons) if reverse_player else train.wagons
        vehicle_x = (loco_x + consist_width - loco_width
                     if reverse_player else loco_x)
        travelled = 0.0
        for wagon in player_wagons:
            vehicle_width = loco_width if wagon.is_loco else car_width
            vehicle_image = self.loco_image if wagon.is_loco else self.car_image
            is_rear_cab = wagon.is_loco and wagon.index == len(train.wagons) - 1
            if is_rear_cab and vehicle_image is not None:
                vehicle_image = pygame.transform.flip(vehicle_image, True, False)
            if vehicle_x + vehicle_width >= -loco_width and vehicle_x <= width + loco_width:
                if vehicle_image is not None:
                    sprite = pygame.transform.smoothscale(vehicle_image, (max(1, vehicle_width), max(1, loco_height)))
                    self._draw_doors(
                        sprite, vehicle_image, vehicle_width, loco_height,
                        is_loco=wagon.is_loco, is_rear_cab=is_rear_cab
                    )
                    self._draw_door_indicators(
                        sprite, vehicle_image, vehicle_width, loco_height,
                        is_loco=wagon.is_loco, is_rear_cab=is_rear_cab,
                        elapsed=elapsed, active=door_closing
                    )
                    center_x = vehicle_x + vehicle_width / 2
                    wagon_position = (
                        train.position - max(
                            0.0, train.consist_length_m - train.loco_length_m
                        ) + travelled
                        if reverse_player else
                        max(0.0, train.position - travelled)
                    )
                    center_y = rail_y_at(center_x) + self._train_track_offset(
                        track_network, train, wagon_position
                    ) * scale
                    surface.blit(sprite, (round(vehicle_x), round(center_y - loco_height + 4)))
                else:
                    center_x = vehicle_x + vehicle_width / 2
                    wagon_position = (
                        train.position - max(
                            0.0, train.consist_length_m - train.loco_length_m
                        ) + travelled
                        if reverse_player else
                        max(0.0, train.position - travelled)
                    )
                    center_y = rail_y_at(center_x) + self._train_track_offset(
                        track_network, train, wagon_position
                    ) * scale
                    pygame.draw.rect(surface, (205, 210, 215) if wagon.is_loco else (185, 190, 196), (round(vehicle_x), round(center_y - 48 + 4), vehicle_width, 48))
            vehicle_x += -vehicle_width if reverse_player else vehicle_width
            travelled += vehicle_width / scale

        # Draw AI trains using the same vehicle sprites and shared world camera.
        for bot_train in (other_trains or []):
            reverse = getattr(bot_train, "direction", 1) < 0
            bot_x = (line.path.total_length - bot_train.position
                     - bot_train.loco_length_m - camera_x) * scale
            bot_loco_width = max(1, round(bot_train.loco_length_m * scale))
            bot_car_width = max(1, round(bot_train.car_length_m * scale))
            bot_vehicle_x = bot_x
            travelled = 0.0
            wagons = reversed(bot_train.wagons) if reverse else bot_train.wagons
            for wagon in wagons:
                vehicle_width = bot_loco_width if wagon.is_loco else bot_car_width
                vehicle_image = self.loco_image if wagon.is_loco else self.car_image
                is_rear_cab = wagon.is_loco and wagon.index == len(bot_train.wagons) - 1
                if is_rear_cab and vehicle_image is not None:
                    vehicle_image = pygame.transform.flip(vehicle_image, True, False)
                vehicle_x = bot_vehicle_x
                if bot_vehicle_x + vehicle_width >= -bot_loco_width and bot_vehicle_x <= width + bot_loco_width:
                    wagon_position = (
                        bot_train.position + travelled if reverse
                        else bot_train.position - travelled
                    )
                    center_y = rail_y_at(vehicle_x + vehicle_width / 2) + self._train_track_offset(
                        track_network, bot_train, wagon_position
                    ) * scale
                    if vehicle_image is not None:
                        sprite = pygame.transform.smoothscale(
                            vehicle_image, (max(1, vehicle_width), max(1, loco_height))
                        )
                        if getattr(bot_train, "doors_open", False):
                            saved_door_amount = self.door_open_amount
                            self.door_open_amount = 1.0
                            self._draw_doors(
                                sprite, vehicle_image, vehicle_width, loco_height,
                                is_loco=wagon.is_loco, is_rear_cab=is_rear_cab
                            )
                            self.door_open_amount = saved_door_amount
                        player_tracks = set(getattr(
                            train, "occupied_track_indices", {getattr(train, "track_index", 1)}
                        ))
                        bot_tracks = set(getattr(
                            bot_train, "occupied_track_indices", {getattr(bot_train, "track_index", 1)}
                        ))
                        if not player_tracks.intersection(bot_tracks):
                            self._dim_train_sprite(sprite)
                        surface.blit(sprite, (round(vehicle_x), round(center_y - loco_height + 4)))
                    else:
                        pygame.draw.rect(
                            surface, (130, 150, 170),
                            (round(vehicle_x), round(center_y - 44), vehicle_width, 44)
                        )
                travelled += vehicle_width / scale
                bot_vehicle_x += -vehicle_width if reverse else vehicle_width
            if -80 < bot_x < width + 80:
                bot_label = self.small_font.render(
                    getattr(bot_train, "display_name", "Бот"),
                    True, (175, 205, 235)
                )
                surface.blit(bot_label, (round(bot_x), max(220, round(rail_y_at(bot_x) - 68))))

        # Foreground shell for the opposing tunnel. It is deliberately drawn
        # after both player and AI trains, so the tunnel sits in front of them.
        # When the player is not occupying this lane it becomes translucent.
        if track_network is not None and self.tunnel_image is not None:
            opposing_lane_index = next((
                index for index in range(len(track_network.lanes))
                if index != track_network.main_lane
            ), None)
            if opposing_lane_index is not None:
                occupied_tracks = set(getattr(
                    train, "occupied_track_indices", {getattr(train, "track_index", track_network.main_lane)}
                ))
                tunnel_alpha = 255 if opposing_lane_index in occupied_tracks else 112
                opposing_offset = self._lane_offset_pixels(
                    track_network.lanes[opposing_lane_index], scale
                )
                opposing_tunnel_height = tunnel_height
                opposing_tunnel_width = max(1, round(
                    opposing_tunnel_height * self.tunnel_image.get_width()
                    / self.tunnel_image.get_height()
                ))
                overlay_key = (
                    id(self.tunnel_image), opposing_tunnel_width,
                    opposing_tunnel_height, tunnel_alpha,
                )
                if overlay_key not in self._opposing_tunnel_cache:
                    overlay_tile = pygame.transform.smoothscale(
                        self.tunnel_image,