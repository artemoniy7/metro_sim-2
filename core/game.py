"""Main game state and scene manager."""
import pygame
from settings import BACKGROUND_COLOR, WINDOW_SIZE, DATA_DIR, ASSETS_DIR
from core.train import Train
from core.bot import BotTrain
from core.opposing_bot import OpposingBot
from core.camera import Camera
from core.line import Line
from core.track_network import TrackNetwork
from core.station_simulation import StationSimulation
from systems.loader import load_json
from systems.renderer import Renderer
from systems.input import InputController
from systems.audio import AudioSystem


class Game:
    def __init__(self, line_file=None, train_file=None, start_position=0.0, end_position=None):
        self.renderer = Renderer()
        self.controls = InputController()
        self.audio = AudioSystem()
        line_path = DATA_DIR / "lines" / (line_file or "line_9.json")
        self.line_data = load_json(line_path, default={})
        line_id = self.line_data.get("line_id", f"line_{self.line_data.get('line_number', 9)}")
        # Start directly on the selected line, at the selected station.
        self.line = Line(self.line_data)
        track_data = load_json(DATA_DIR / "tracks" / f"{line_id}.json", default={})
        self.track_network = TrackNetwork(self.line, track_data)
        self.renderer.configure_line_station_sprites(line_id)
        configure_station_joints = getattr(self.audio, "configure_station_joint_sounds", None)
        if callable(configure_station_joints):
            configure_station_joints(self.line.stations)
        self.station_simulation = StationSimulation(self.line.stations)
        configure_announcements = getattr(self.audio, "configure_station_announcements", None)
        if callable(configure_announcements):
            configure_announcements(len(self.line.stations), line_id)
        train_path = DATA_DIR / "trains" / (train_file or "81-760.json")
        train_data = load_json(train_path, default={})
        self.train = Train(train_data)
        self.line_max_speed = self.train.max_speed
        self.train.position = max(0.0, float(start_position))
        self.end_position = float(end_position) if end_position is not None else self.line.path.total_length
        # Close view of the locomotive, with mouse-wheel zoom and consist panning.
        display_surface = pygame.display.get_surface()
        viewport_size = display_surface.get_size() if display_surface else WINDOW_SIZE
        self.camera = Camera(viewport_size, zoom=2.8)
        self.elapsed = 0.0
        self.doors_open = False
        # The control panel starts hidden; only its small handle remains visible.
        self.control_panel_open = False
        self.control_panel_y = None
        self.control_panel_images = {}
        self.control_panel_scaled_cache = {}
        for image_name in ("speed-menu.png", "door-menu.png"):
            image_path = ASSETS_DIR / "ui" / "train-ui" / "81-760" / image_name
            try:
                image = pygame.image.load(str(image_path)).convert_alpha()
                # Pure white in these source mockups is the transparent canvas.
                image.set_colorkey((255, 255, 255))
                self.control_panel_images[image_name] = image
            except (pygame.error, OSError):
                self.control_panel_images[image_name] = None
        # The player's initial position is reserved; AI trains enter every
        # two minutes and are recycled to the line start after the terminus.
        self.bot_trains = []
        self.opposing_trains = []
        self.bot_dispatch_interval = 120.0
        self.bots_enabled = self.train.position <= 0.01
        self.bot_dispatch_timer = 0.0
        self.bot_number = 0
        # Put the first AI train into service immediately; subsequent trains
        # are dispatched every two minutes.
        # AI traffic is enabled only when starting from the line origin.
        if self.train.position <= 0.01:
            self._dispatch_bot()
        # A few opposing services make the second track active at several
        # points along the route without overcrowding the view.
        if line_id == "line_9":
            for position in (3500.0, 18000.0, 33000.0):
                self._dispatch_opposing_train(position)

    def _dispatch_bot(self):
        train_data = load_json(DATA_DIR / "trains" / "81-760.json", default={})
        self.bot_number += 1
        # Keep one bot farther down the line. All other bots queue just beyond
        # Altufyevo's platform, spaced by roughly one train length so they do
        # not spawn inside the player or inside one another.
        first_station = self.line.stations[0]
        station_position = float(first_station.get("position", 0.0))
        if self.bot_number == 1:
            start_position = min(2000.0, self.line.path.total_length - 2500.0)
        else:
            start_position = station_position + 175.0 + (self.bot_number - 2) * 180.0
        bot = BotTrain(train_data, start_position=start_position)
        bot.train.display_name = f"Состав {self.bot_number}"
        self.bot_trains.append(bot)

    def _dispatch_opposing_train(self, start_position):
        train_data = load_json(DATA_DIR / "trains" / "81-760.json", default={})
        opposing = OpposingBot(
            train_data,
            start_position=min(float(start_position), self.line.path.total_length - 1800.0),
        )
        opposing.train.display_name = "Встречный состав"
        self.opposing_trains.append(opposing)

    def _control_panel_metrics(self, width, height):
        panel_height = min(height - 36, max(210, int(height * 0.34)))
        handle_height = 36
        target_y = height - panel_height if self.control_panel_open else height - handle_height
        return panel_height, handle_height, target_y

    def _toggle_control_panel(self):
        self.control_panel_open = not self.control_panel_open

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
            self.control_panel_open = True
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
            self.control_panel_open = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_v:
            # Doors may only be operated while the train is completely stopped.
            if abs(self.train.speed) < 0.05:
                self.doors_open = not self.doors_open
                self.train.doors_open = self.doors_open
                play_door_sound = getattr(self.audio, "play_door_sound", None)
                if callable(play_door_sound):
                    play_door_sound()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_i:
            toggle_announcer = getattr(self.audio, "toggle_station_announcer", None)
            if callable(toggle_announcer):
                toggle_announcer(self.train, self.line)
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_q, pygame.K_e):
            direction = -1 if event.key == pygame.K_q else 1
            self.track_network.request_lane_change(
                self.train, direction, ([self.train]
                                        + [bot.train for bot in self.bot_trains]
                                        + [bot.train for bot in self.opposing_trains])
            )
        elif event.type == pygame.MOUSEWHEEL:
            self.camera.zoom_by(event.y * 0.15)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                display = pygame.display.get_surface()
                if display is not None:
                    width, height = display.get_size()
                    if self.control_panel_y is None:
                        self.control_panel_y = float(height - 36)
                    handle = pygame.Rect(width // 2 - 48, round(self.control_panel_y), 96, 36)
                    if handle.collidepoint(event.pos):
                        self._toggle_control_panel()
            elif event.button == 4:
                self.camera.zoom_by(0.15)
            elif event.button == 5:
                self.camera.zoom_by(-0.15)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
            self.camera.pan(-1, self.train)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
            self.camera.pan(1, self.train)

        self.controls.handle_event(event, self.train)

    def update(self, dt):
        self.elapsed += dt
        display = pygame.display.get_surface()
        if display is not None:
            width, height = display.get_size()
            _, _, target_y = self._control_panel_metrics(width, height)
            if self.control_panel_y is None:
                self.control_panel_y = float(height - 36)
            # A steady slide takes roughly half a second on a typical display.
            distance = target_y - self.control_panel_y
            step = 620.0 * dt
            if abs(distance) <= step:
                self.control_panel_y = float(target_y)
            else:
                self.control_panel_y += step if distance > 0 else -step

            # Reframe the scene as the panel rises: pull back slightly and
            # move the train/track upward so the panel does not cover them.
            panel_height, _, _ = self._control_panel_metrics(width, height)
            visible_ratio = max(0.0, min(1.0,
                (height - self.control_panel_y) / float(panel_height)))
            self.camera.panel_zoom_factor = 1.0 - 0.12 * visible_ratio
            self.camera.panel_vertical_offset = panel_height * 0.55 * visible_ratio
        self.controls.update(self.train, dt)
        # Do not retain a traction command while the doors are open.
        if self.doors_open and self.train.controller_notch > 0:
            self.train.controller_notch = 0
        self.train.doors_open = self.doors_open

        self.bot_dispatch_timer += dt
        if self.bots_enabled and self.bot_dispatch_timer >= self.bot_dispatch_interval:
            self.bot_dispatch_timer -= self.bot_dispatch_interval
            self._dispatch_bot()

        # ALS-ARS sees every train, including the player, before any train
        # updates this frame. This keeps following trains from driving through.
        self.line.traffic_trains = [self.train] + [bot.train for bot in self.bot_trains]
        self.train.update(dt, self.line)
        self.track_network.update_train(self.train)
        if self.train.position >= self.end_position:
            self.train.position = self.end_position
            self.train.speed = 0.0
            self.train.controller_notch = 0
        for opposing in list(self.opposing_trains):
            opposing.update(dt, self.line)
            if opposing.train.position <= 0.5:
                # Turn the service around at Altufyevo for continuous testing.
                opposing.train.position = max(0.0, self.line.path.total_length - 1800.0)
                opposing.train.speed = 0.0
                opposing.train.acceleration_state = 0.0
                opposing.train.controller_notch = 0
                opposing.state = "running"
                opposing.target_station = None
                opposing.dwell_timer = 0.0

        for bot in list(self.bot_trains):
            bot.update(dt, self.line, self.audio,
                       seconds_to_dispatch=self.bot_dispatch_interval - self.bot_dispatch_timer)
            self.track_network.update_train(bot.train)
            if (bot.state != "dwelling"
                    and bot.train.position >= self.line.path.total_length - 0.5):
                # Remove the train from the terminus and put it at the back of
                # the service queue. The player's own train is never recycled.
                slot_index = self.bot_trains.index(bot)
                self.bot_trains.remove(bot)
                # Recycle into the same staggered queue beyond Altufyevo.
                bot.train.position = (
                    min(2000.0, self.line.path.total_length - 2500.0)
                    if slot_index == 0
                    else float(self.line.stations[0].get("position", 0.0))
                    + 175.0 + slot_index * 180.0
                )
                bot.train.speed = 0.0
                bot.train.acceleration_state = 0.0
                bot.train.controller_notch = 0
                bot.state = "running"
                bot.target_station = None
                bot.dwell_timer = 0.0
                bot.informer_started = False
                bot.informer_timer = 0.0
                bot.closed_for_departure = False
                self.bot_trains.append(bot)
        self.line.traffic_trains = [self.train] + [bot.train for bot in self.bot_trains]
        self.line.update_signals(self.line.traffic_trains)
        # The opposing track has its own block states and train occupancy.
        self.line.update_signals(
            [opposing.train for opposing in self.opposing_trains],
            signals=self.line.opposing_signals,
            direction=-1,
        )
        self.camera.follow(self.train, self.line.path.total_length)
        self.audio.update(self.train, dt, self.camera)
        self.station_simulation.update(dt, self.train, self.doors_open)
        update_station_ambience = getattr(self.audio, "update_station_ambience", None)
        if callable(update_station_ambience):
            update_station_ambience(self.station_simulation, self.train)
        update_announcer = getattr(self.audio, "update_station_announcer", None)
        if callable(update_announcer):
            update_announcer(self.train, dt)

    def render(self, surface):
        # The game window is borderless fullscreen; keep camera geometry in
        # sync with the actual render target rather than the menu's design size.
        viewport_size = surface.get_size()
        if (self.camera.width, self.camera.height) != viewport_size:
            self.camera.width, self.camera.height = viewport_size
            self.camera.focus_screen_x = viewport_size[0] * 0.36
            self.camera.follow(self.train, self.line.path.total_length)
        surface.fill(BACKGROUND_COLOR)
        self.renderer.draw_scene(
            surface, self.line, self.train, self.camera, self.elapsed,
            doors_open=self.doors_open,
            door_closing=getattr(self.audio, "door_ring_active", False),
            other_trains=([bot.train for bot in self.bot_trains]
                          + [bot.train for bot in self.opposing_trains]),
            station_simulation=self.station_simulation,
            track_network=self.track_network,
        )
        if not self.doors_open and self.renderer.door_open_amount <= 0.0:
            stop_door_ring = getattr(self.audio, "stop_door_ring", None)
            if callable(stop_door_ring):
                stop_door_ring()

        # Sliding placeholder for the future 81-760 cab controls.
        width, height = surface.get_size()
        panel_height, handle_height, target_y = self._control_panel_metrics(width, height)
        if self.control_panel_y is None:
            self.control_panel_y = float(height - handle_height)
        panel_y = max(0, min(height, round(self.control_panel_y)))
        panel_rect = pygame.Rect(0, panel_y, width, height - panel_y)
        pygame.draw.rect(surface, (1, 145, 197), panel_rect)
        pygame.draw.line(surface, (0, 69, 105), (0, panel_y), (width, panel_y), 3)

        # The two 81-760 photo panels travel with the sliding background.
        # Keep their proportions and cache each scaled size to avoid per-frame resampling.
        content_top = panel_y + handle_height + 8
        content_bottom = height - 10
        content_height = max(1, content_bottom - content_top)
        image_gap = 6
        slot_height = max(1, (content_height - image_gap) // 2)
        max_image_width = max(1, int(width * 0.92))
        for image_name, slot_index, size_factor in (
            ("speed-menu.png", 0, 1.0),
            ("door-menu.png", 1, 0.88),
        ):
            source_image = self.control_panel_images.get(image_name)
            if source_image is None:
                continue
            target_height = max(1, int(slot_height * size_factor))
            target_width = min(
                max_image_width,
                max(1, round(target_height * source_image.get_width() / source_image.get_height()))
            )
            if target_width / source_image.get_width() > target_height / source_image.get_height():
                target_width = max(1, round(target_height * source_image.get_width() / source_image.get_height()))
            cache_key = (image_name, target_width, target_height)
            scaled_image = self.control_panel_scaled_cache.get(cache_key)
            if scaled_image is None:
                scale = min(
                    max_image_width / source_image.get_width(),
                    target_height / source_image.get_height(),
                )
                scaled_size = (
                    max(1, round(source_image.get_width() * scale)),
                    max(1, round(source_image.get_height() * scale)),
                )
                cache_key = (image_name, *scaled_size)
                scaled_image = self.control_panel_scaled_cache.get(cache_key)
                if scaled_image is None:
                    scaled_image = pygame.transform.smoothscale(source_image, scaled_size)
                    self.control_panel_scaled_cache[cache_key] = scaled_image
            slot_y = content_top + slot_index * (slot_height + image_gap)
            image_x = (width - scaled_image.get_width()) // 2
            image_y = slot_y + max(0, (slot_height - scaled_image.get_height()) // 2)
            surface.blit(scaled_image, (image_x, image_y))

        handle_rect = pygame.Rect(width // 2 - 48, panel_y, 96, handle_height)
        pygame.draw.rect(surface, (0, 91, 133), handle_rect, border_radius=8)
        pygame.draw.rect(surface, (190, 225, 238), handle_rect, width=2, border_radius=8)
        center_x = handle_rect.centerx
        if self.control_panel_open:
            arrow = [(center_x - 10, panel_y + 13),
                     (center_x + 10, panel_y + 13),
                     (center_x, panel_y + 24)]
        else:
            arrow = [(center_x - 10, panel_y + 23),
                     (center_x + 10, panel_y + 23),
                     (center_x, panel_y + 12)]
        pygame.draw.polygon(surface, (245, 250, 252), arrow)
