"""Modern driver-cab overlay for the metro simulator."""
import math
import pygame


class DriverCabUI:
    BG = (12, 17, 22)
    PANEL = (27, 38, 45)
    PANEL_EDGE = (63, 83, 91)
    TURQUOISE = (38, 157, 157)
    TEXT = (231, 239, 240)
    MUTED = (145, 164, 169)
    WHITE_BUTTON = (177, 190, 192)
    GREEN = (22, 91, 62)

    NOTCHES = (-3, -2, -1, 0, 1, 2, 3, 4)
    NOTCH_LABELS = ("Т3", "Т2", "Т1", "0", "ход1", "ход2", "ход3", "ход4")

    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.SysFont("arial", 18, bold=True)
        self.small = pygame.font.SysFont("arial", 14)
        self.tiny = pygame.font.SysFont("arial", 11)
        self.title = pygame.font.SysFont("arial", 20, bold=True)
        self.drawer = None
        self.buttons = {}
        self.dragging_lever = False
        self.pressed_button = None
        self.door_flash = 0.0
        self._next_restriction = None
        self.window_distance = 1800.0
        self._zone_cache = []

    def _text(self, surface, value, pos, color=None, font=None):
        surface.blit((font or self.small).render(str(value), True, color or self.TEXT), pos)

    def _button(self, surface, key, label, rect, active=False, color=None):
        self.buttons[key] = rect
        fill = color or (self.WHITE_BUTTON if active else (118, 137, 141))
        if self.pressed_button == key:
            fill = tuple(max(0, channel - 24) for channel in fill)
        pygame.draw.rect(surface, fill, rect, border_radius=7)
        pygame.draw.rect(surface, (225, 235, 235), rect, 1, border_radius=7)
        ink = (19, 31, 34) if active or color else (30, 40, 43)
        text = self.font.render(label, True, ink)
        surface.blit(text, text.get_rect(center=rect.center))

    def handle_event(self, event, train):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_lever = False
            self.pressed_button = None
            return True
        if event.type == pygame.MOUSEMOTION and self.dragging_lever and self.drawer == "motion":
            self._set_notch_from_y(event.pos[1], train)
            return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        self.pressed_button = next((key for key, rect in self.buttons.items()
                                    if rect.collidepoint(event.pos)), None)
        if self.dragging_lever:
            self._set_notch_from_y(event.pos[1], train)
            return True

        for key, rect in list(self.buttons.items()):
            if not rect.collidepoint(event.pos):
                continue
            if key.startswith("tab_"):
                name = key[4:]
                self.drawer = None if self.drawer == name else name
            elif key == "left_side":
                return {"door_side": "left"}
            elif key == "right_side":
                return {"door_side": "right"}
            elif key == "open_left":
                return {"open_doors": "left"}
            elif key == "open_right":
                return {"open_doors": "right"}
            elif key == "close_doors":
                self.door_flash = 0.22
                return {"close_doors": True}
            elif key == "lever":
                self.dragging_lever = True
                self._set_notch_from_y(event.pos[1], train)
            return True
        return False

    def _set_notch_from_y(self, y, train):
        rect = self.buttons.get("lever_track")
        if rect is None:
            return
        t = max(0.0, min(1.0, (y - rect.top) / max(1, rect.height)))
        index = round((1.0 - t) * (len(self.NOTCHES) - 1))
        train.controller_notch = self.NOTCHES[index]

    def update(self, dt):
        self.door_flash = max(0.0, self.door_flash - dt)

    def _draw_route_map(self, surface, line, train):
        width, _ = surface.get_size()
        box = pygame.Rect(18, 16, width - 36, 104)
        pygame.draw.rect(surface, (22, 30, 36), box, border_radius=12)
        pygame.draw.rect(surface, (73, 88, 94), box, 1, border_radius=12)
        self._text(surface, "ПУТЬ ВПЕРЁДИ", (box.x + 18, box.y + 9), self.MUTED, self.small)

        track_y = box.y + 64
        left = box.x + 34
        right = box.right - 24
        pygame.draw.line(surface, (67, 76, 81), (left, track_y), (right, track_y), 8)
        pygame.draw.line(surface, (36, 43, 48), (left, track_y), (right, track_y), 2)
        pygame.draw.line(surface, (240, 244, 242), (left, track_y - 20),
                         (left, track_y + 20), 3)
        self._text(surface, "ПОЕЗД", (left - 8, track_y + 22), self.TEXT, self.tiny)

        direction = 1 if getattr(train, "direction", 1) >= 0 else -1
        current_speed = abs(float(train.speed)) * 3.6
        current_limit = float(getattr(train, "current_speed_limit_mps", train.max_speed)) * 3.6
        saved_indication = getattr(train.als, "indication_kmh", 0.0)
        saved_blocks = getattr(train.als, "free_blocks_ahead", 0)
        samples = []
        step = 35.0
        for distance in range(0, int(self.window_distance) + 1, int(step)):
            position = float(train.position) + direction * distance
            position = max(0.0, min(float(line.path.total_length), position))
            limit, _ = line.block_indication(position, train)
            limit = min(90.0, float(limit), float(train.max_speed) * 3.6)
            if distance == 0:
                current_limit = min(current_limit, limit) if current_limit > 0 else limit
            samples.append((float(distance), limit))
        train.als.indication_kmh = saved_indication
        train.als.free_blocks_ahead = saved_blocks

        px_per_m = (right - left) / self.window_distance
        self._next_restriction = None
        previous_limit = samples[0][1] if samples else current_limit
        for distance, limit in samples[1:]:
            if limit < previous_limit - 0.1:
                x = int(left + distance * px_per_m)
                if self._next_restriction is None:
                    self._next_restriction = (distance, limit)
                required_distance = max(0.0, ((current_speed / 3.6) ** 2 - (limit / 3.6) ** 2) / (2 * 0.65)) + 60.0
                too_fast = current_speed > limit + 1.0 and distance <= required_distance
                pygame.draw.rect(surface, (132, 143, 148), (x - 3, track_y - 22, 7, 44))
                pygame.draw.line(surface, (35, 42, 47), (x, track_y - 26), (x, track_y + 26), 1)
            previous_limit = limit

        for station in line.stations:
            distance = (float(station.get("position", 0)) - float(train.position)) * direction
            if 0 <= distance <= self.window_distance:
                x = int(left + distance * px_per_m)
                pygame.draw.circle(surface, (184, 198, 200), (x, track_y), 4)
        self._text(surface, f"{current_limit:.0f}", (box.right - 48, box.y + 10),
                   (230, 202, 104), self.font)

    def _draw_tabs(self, surface):
        width, height = surface.get_size()
        labels = (("motion", "ХОД"), ("doors", "ДВЕРИ"), ("speed", "СКОРОСТЬ"))
        total_w = min(480, width - 36)
        x0 = 18
        gap = 8
        bw = (total_w - gap * 2) // 3
        y = height - 58
        for index, (key, label) in enumerate(labels):
            rect = pygame.Rect(x0 + index * (bw + gap), y, bw, 42)
            self._button(surface, f"tab_{key}", label, rect,
                         active=self.drawer == key, color=self.TURQUOISE if self.drawer == key else None)

    def _drawer_rect(self, surface):
        width, height = surface.get_size()
        rect = pygame.Rect(18, max(136, height - 350), min(520, width - 36), 278)
        pygame.draw.rect(surface, self.PANEL, rect, border_radius=14)
        pygame.draw.rect(surface, self.PANEL_EDGE, rect, 1, border_radius=14)
        return rect

    def _draw_motion(self, surface, train):
        panel = self._drawer_rect(surface)
        self._text(surface, "УПРАВЛЕНИЕ ХОДОМ", (panel.x + 18, panel.y + 12), self.TEXT, self.title)
        track = pygame.Rect(panel.x + 42, panel.y + 58, 12, 184)
        self.buttons["lever_track"] = track
        pygame.draw.line(surface, (8, 13, 15), track.midtop, track.midbottom, 7)
        for index, (notch, label) in enumerate(zip(self.NOTCHES, self.NOTCH_LABELS)):
            y = track.bottom - int(index * track.height / (len(self.NOTCHES) - 1))
            pygame.draw.line(surface, (8, 13, 15), (track.centerx - 8, y), (track.centerx + 8, y), 2)
            self._text(surface, label, (panel.x + 105, y - 9),
                       (230, 238, 239) if train.controller_notch == notch else self.MUTED,
                       self.font if train.controller_notch == notch else self.small)
        current_index = self.NOTCHES.index(max(-3, min(4, int(train.controller_notch))))
        handle_y = track.bottom - int(current_index * track.height / (len(self.NOTCHES) - 1))
        handle = pygame.Rect(track.centerx - 24, handle_y - 8, 48, 16)
        self.buttons["lever"] = pygame.Rect(track.x - 24, track.y - 8, track.width + 48, track.height + 16)
        pygame.draw.rect(surface, (150, 160, 163), handle, border_radius=4)
        pygame.draw.rect(surface, (205, 214, 215), handle, 1, border_radius=4)
        self._text(surface, f"ТЕКУЩЕЕ ПОЛОЖЕНИЕ: {train.controller_label}",
                   (panel.x + 245, panel.y + 75), self.TEXT, self.font)
        self._text(surface, "Перетащи ручку или выбери положение по шкале",
                   (panel.x + 245, panel.y + 108), self.MUTED, self.small)
        self._text(surface, f"Скорость  {abs(train.speed) * 3.6:.1f} км/ч",
                   (panel.x + 245, panel.y + 150), self.TEXT, self.font)

    def _draw_doors(self, surface, train, game):
        panel = self._drawer_rect(surface)
        self._text(surface, "УПРАВЛЕНИЕ ДВЕРЬМИ", (panel.x + 18, panel.y + 12), self.TEXT, self.title)
        y = panel.y + 70
        self._button(surface, "left_side", "ЛЕВАЯ СТОРОНА",
                     pygame.Rect(panel.x + 22, y, 190, 48),
                     active=game.selected_door_side == "left")
        self._button(surface, "right_side", "ПРАВАЯ СТОРОНА",
                     pygame.Rect(panel.x + 230, y, 190, 48),
                     active=game.selected_door_side == "right")
        self._button(surface, "open_left", "ОТКРЫТЬ ЛЕВЫЕ",
                     pygame.Rect(panel.x + 22, y + 62, 190, 42),
                     active=game.doors_open and game.selected_door_side == "left")
        self._button(surface, "open_right", "ОТКРЫТЬ ПРАВЫЕ",
                     pygame.Rect(panel.x + 230, y + 62, 190, 42),
                     active=game.doors_open and game.selected_door_side == "right")
        close_color = (47, 145, 91) if self.door_flash > 0 else self.GREEN
        self._button(surface, "close_doors", "ЗАКРЫТЬ ДВЕРИ",
                     pygame.Rect(panel.x + 22, y + 122, 398, 48),
                     active=self.door_flash > 0, color=close_color)
        status = "ДВЕРИ ОТКРЫТЫ" if game.doors_open else "ДВЕРИ ЗАКРЫТЫ"
        self._text(surface, status, (panel.x + 24, y + 184),
                   (117, 222, 171) if game.doors_open else self.MUTED, self.font)
        if abs(train.speed) >= 0.05:
            self._text(surface, "Открытие доступно только при остановке поезда",
                       (panel.x + 22, panel.bottom - 28), (225, 187, 105), self.small)

    def _draw_speedometer(self, surface, train, line):
        width, height = surface.get_size()
        panel = self._drawer_rect(surface)
        panel.width = min(390, panel.width)
        panel.x = width - panel.width - 18
        pygame.draw.rect(surface, (5, 8, 11), panel, border_radius=14)
        pygame.draw.rect(surface, self.PANEL_EDGE, panel, 1, border_radius=14)
        self._text(surface, "СКОРОСТЕМЕР", (panel.x + 18, panel.y + 12), self.TEXT, self.title)

        center = (panel.centerx, panel.y + 174)
        radius = 112
        pygame.draw.circle(surface, (11, 15, 18), center, radius + 12)
        pygame.draw.circle(surface, (83, 94, 99), center, radius + 6, 2)
        future = self._next_restriction
        future_limit = future[1] if future else float(getattr(train, "current_speed_limit_mps", train.max_speed)) * 3.6
        future_distance = future[0] if future else float("inf")
        speed_now = abs(float(train.speed)) * 3.6
        stop_distance = max(0.0, ((speed_now / 3.6) ** 2 - (future_limit / 3.6) ** 2) / (2 * 0.65)) + 60.0
        future_is_red = speed_now > future_limit + 1.0 and future_distance <= stop_distance
        for value in range(0, 91, 5):
            angle = math.radians(135 + value / 90 * 270)
            outer = (center[0] + math.cos(angle) * radius,
                     center[1] + math.sin(angle) * radius)
            inner = (center[0] + math.cos(angle) * (radius - (13 if value % 10 == 0 else 7)),
                     center[1] + math.sin(angle) * (radius - (13 if value % 10 == 0 else 7)))
            limit = float(getattr(train, "current_speed_limit_mps", train.max_speed)) * 3.6
            color = (128, 140, 145)
            if value > min(limit, future_limit) + 0.1:
                color = (214, 65, 62) if future_is_red else (221, 177, 60)
            pygame.draw.line(surface, color, inner, outer, 3 if value % 10 == 0 else 2)
            if value % 10 == 0:
                tx = center[0] + math.cos(angle) * (radius - 30)
                ty = center[1] + math.sin(angle) * (radius - 30)
                label = self.small.render(str(value), True, self.TEXT)
                surface.blit(label, label.get_rect(center=(int(tx), int(ty))))
        speed = max(0.0, min(90.0, abs(float(train.speed)) * 3.6))
        angle = math.radians(135 + speed / 90 * 270)
        tip = (center[0] + math.cos(angle) * (radius - 42),
               center[1] + math.sin(angle) * (radius - 42))
        pygame.draw.line(surface, (177, 187, 191), center, tip, 4)
        pygame.draw.circle(surface, (195, 205, 208), center, 7)
        speed_text = self.title.render(f"{speed:.0f}", True, self.TEXT)
        surface.blit(speed_text, speed_text.get_rect(center=(center[0], center[1] + 35)))
        self._text(surface, "км/ч", (center[0] - 19, center[1] + 56), self.MUTED, self.tiny)
        limit = float(getattr(train, "current_speed_limit_mps", train.max_speed)) * 3.6
        self._text(surface, f"РАЗРЕШЕНО: {limit:.0f} км/ч",
                   (panel.x + 22, panel.bottom - 42), (226, 190, 88), self.font)

    def render(self, surface, line, train, game):
        self.buttons.clear()
        self._draw_route_map(surface, line, train)
        if self.drawer == "motion":
            self._draw_motion(surface, train)
        elif self.drawer == "doors":
            self._draw_doors(surface, train, game)
        elif self.drawer == "speed":
            self._draw_speedometer(surface, train, line)
        self._draw_tabs(surface)
