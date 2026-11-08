"""Main game state and scene manager."""
import pygame
from settings import BACKGROUND_COLOR, WINDOW_SIZE, DATA_DIR
from core.train_models import create_train
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
        line_path = DATA_DIR / "lines" / (line_file or "line_9.json")
        self.line_data = load_json(line_path, default={})
        line_id = self.line_data.get("line_id", f"line_{self.line_data.get('line_number', 9)}")
        local_track_layout = load_json(
            DATA_DIR / "track_layouts" / f"{line_id}.json", default={}
        )
        # The line's published chainage starts at Nekrasovka (0 m), but
        # the simulator clamps train positions to the non-negative route.
        # Add a virtual 500 m approach before the origin for line 15, shifting
        # station chainages without editing the source line JSON.
        local_origin_extension = float(
            local_track_layout.get("origin_extension_m", 0.0)
        ) if line_id == "line_15" else 0.0
        if local_origin_extension > 0.0:
            points = self.line_data.get("points", [])
            if len(points) >= 2:
                first, second = points[0], points[1]
                dx, dy = float(second[0]) - float(first[0]), float(second[1]) - float(first[1])
                segment_length = (dx * dx + dy * dy) ** 0.5
                if segment_length > 0:
                    extension_point = [
                        float(first[0]) - dx / segment_length * local_origin_extension,
                        float(first[1]) - dy / segment_length * local_origin_extension,
                    ]
                    self.line_data["points"] = [extension_point] + points
                    for station in self.line_data.get("stations", []):
                        station["position"] = float(station.get("position", 0.0)) + local_origin_extension

        # Start directly on the selected line, at the selected station.
        self.line = Line(self.line_data)
        track_data = load_json(DATA_DIR / "tracks" / f"{line_id}.json", default={})
        self.track_network = TrackNetwork(self.line, track_data, local_track_layout)
        self.renderer.configure_line_station_sprites(line_id)
        train_path = DATA_DIR / "trains" / (train_file or "81-760.json")
        train_data = load_json(train_path, default={})
        self.train = create_train(train_data)
        # Always spawn the player on the configured main track, not on the opposing track.
        self.train.track_index = self.track_network.main_lane
        self.renderer.configure_train_model(self.train)
        self.audio = AudioSystem(model_id=self.train.model_id)
        configure_station_joints = getattr(self.audio, "configure_station_joint_sounds", None)
        if callable(configure_station_joints):
            configure_station_joints(self.line.stations)
        self.station_simulation = StationSimulation(self.line.stations)
        configure_announcements = getattr(self.audio, "configure_station_announcements", None)
        if callable(configure_announcements):
            configure_announcements(len(self.line.stations), line_id)
        self.line_max_speed = self.train.max_speed
        self.train.position = max(0.0, float(start_position) + local_origin_extension)
        self.end_position = (
            float(end_position) + local_origin_extension
            if end_position is not None else self.line.path.total_length
        )
        # Close view of the locomotive, with mouse-wheel zoom and consist panning.
        display_surface = pygame.display.get_surface()
        viewport_size = display_surface.get_size() if display_surface else WINDOW_SIZE
        self.camera = Camera(viewport_size, zoom=2.8)
        self.elapsed = 0.0
        self.doors_open = False
        self.selected_door_side = None
        self.train.reverser_position = 0  # -1 reverse, 0 neutral, +1 forward (relative to active cab)
        self.train.active_cab = 0
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
        train_data = load_json(DATA_DIR / "trains" / f"{self.train.model_id}.json", default={})
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
        bot.train.track_index = self.track_network.main_lane
        bot.train.display_name = f"Состав {self.bot_number}"
        self.bot_trains.append(bot)

    def _dispatch_opposing_train(self, start_position):
        train_data = load_json(DATA_DIR / "trains" / f"{self.train.model_id}.json", default={})
        opposing = OpposingBot(
            train_data,
            start_position=min(float(start_position), self.line.path.total_length - 1800.0),
        )
        opposing.train.display_name = "Встречный состав"
        self.opposing_trains.append(opposing)

    def _sync_reverser_direction(self):
        selector = int(getattr(self.train, "reverser_position", 0))
        cab_sign = 1 if self.train.active_cab == 0 else -1
        if selector:
            self.train.direction = selector * cab_sign

    def _open_selected_doors(self, side):
        if self.selected_door_side != side:
            return
        if abs(self.train.speed) >= 0.05 or not self.train.pneumatics.doors_available:
            return
        if not self.doors_open:
            self.doors_open = True
            self.train.doors_open = True
            play_door_sound = getattr(self.audio, "play_door_sound", None)
            if callable(play_door_sound):
                play_door_sound()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif event.type == pygame.KEYDOWN:
            mods = getattr(event, "mod", pygame.key.get_mods())
            shift = bool(mods & pygame.KMOD_SHIFT)
            if shift and event.key == pygame.K_a:
                self.selected_door_side = "left"
            elif shift and event.key == pygame.K_d:
                self.selected_door_side = "right"
            elif event.key == pygame.K_a and not shift:
                self._open_selected_doors("left")
            elif event.key == pygame.K_d and not shift:
                self._open_selected_doors("right")
            elif event.key == pygame.K_v:
                if self.doors_open:
                    self.doors_open = False
                    self.train.doors_open = False
                    play_door_sound = getattr(self.audio, "play_door_sound", None)
                    if callable(play_door_sound):
                        play_door_sound()
                    announce_departure = getattr(self.audio, "announce_departure", None)
                    if callable(announce_departure):
                        announce_departure(self.train, self.line)
            elif event.key in (pygame.K_0, pygame.K_KP0):
                # Cab change is a separate action from the reverser. Permit it
                # whenever the train is stopped, including while doors are open.
                if abs(self.train.speed) < 0.05:
                    self.train.active_cab = 1 - self.train.active_cab
                    self.camera.consist_offset_m = 0.0
                    self._sync_reverser_direction()
            elif event.key == pygame.K_i:
                toggle_announcer = getattr(self.audio, "toggle_station_announcer", None)
                if callable(toggle_announcer):
                    toggle_announcer(self.train, self.line)
            elif event.key == pygame.K_q:
                self.track_network.request_route_selection(self.train, -1)
            elif event.key == pygame.K_e:
                self.track_network.request_route_selection(self.train, 1)
            elif event.key == pygame.K_LEFT:
                self.camera.pan(-1, self.train)
            elif event.key == pygame.K_RIGHT:
                self.camera.pan(1, self.train)
        elif event.type == pygame.MOUSEWHEEL:
            self.camera.zoom_by(event.y * 0.15)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.camera.zoom_by(0.15)
            elif event.button == 5:
                self.camera.zoom_by(-0.15)

        self.controls.handle_event(event, self.train)
        self._sync_reverser_direction()

    def _is_train_in_tunnel(self):
        position = float(self.train.position)
        if position < float(getattr(self.line, "depot_length", 0.0)):
            return False
        for station in self.line.stations:
            center = float(station.get("position", 0.0))
            half_length = float(station.get("length_m", 162.0)) / 2.0
            if abs(position - center) <= half_length:
                return False
        return True

    def update(self, dt):
        self.elapsed += dt
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
        announce_terminal_arrival = getattr(self.audio, "announce_terminal_arrival", None)
        if callable(announce_terminal_arrival):
            announce_terminal_arrival(self.train, self.line)
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
        self.audio.update(
            self.train, dt, self.camera, in_tunnel=self._is_train_in_tunnel()
        )
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
        self.renderer.selected_door_side = self.selected_door_side
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

