"""Driver-cab overlay with circular controls and an announcement console."""
import math
import pygame


class DriverCabUI:
    PANEL = (27, 38, 45)
    PANEL_EDGE = (63, 83, 91)
    TURQUOISE = (38, 157, 157)
    TEXT = (231, 239, 240)
    MUTED = (145, 164, 169)
    WHITE_BUTTON = (177, 190, 192)
    GREEN = (22, 91, 62)
    RED = (190, 49, 47)
    YELLOW = (218, 174, 48)

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
        self.dragging_reverser = False
        self.pressed_button = None
        self.door_flash = 0.0
        self._next_restriction = None
        self.window_distance = 1800.0
        self.announcement_index = 0
        self.announcement_scroll = 0
        self.announcement_items = []
        self.announcement_row_height = 30

    def _text(self, surface, value, pos, color=None, font=None):
        surface.blit((font or self.small).render(str(value), True, color or self.TEXT), pos)

    def _button(self, surface, key, label, rect, active=False, color=None):
        """Draw a true circle in a square hitbox; labels are always outside it."""
        self.buttons[key] = rect
        radius = min(rect.width, rect.height) // 2
        fill = color or (self.WHITE_BUTTON if active else (118, 137, 141))
        if self.pressed_button == key:
            fill = tuple(max(0, channel - 24) for channel in fill)
        pygame.draw.circle(surface, fill, rect.center, radius)
        pygame.draw.circle(surface, (225, 235, 235), rect.center, radius, 2)

    def _rect_button(self, surface, key, label, rect, color=(76, 93, 101), active=False):
        self.buttons[key] = rect
        fill = tuple(max(0, c - 20) for c in color) if self.pressed_button == key else color
        pygame.draw.rect(surface, fill, rect, border_radius=6)
        pygame.draw.rect(surface, (190, 205, 208), rect, 1, border_radius=6)
        text = self.small.render(label, True, self.TEXT)
        surface.blit(text, text.get_rect(center=rect.center))

    def _button_hit(self, key, rect, pos):
        if key in ("lever", "reverser_selector", "announcement_up", "announcement_down") or key.startswith("announcement_item_"):
            return rect.collidepoint(pos)
        radius = min(rect.width, rect.height) // 2
        dx, dy = pos[0] - rect.centerx, pos[1] - rect.centery
        return dx * dx + dy * dy <= radius * radius

    def handle_event(self, event, train):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_lever = False
            self.dragging_reverser = False
            self.pressed_button = None
            return True
        if event.type == pygame.MOUSEMOTION and self.dragging_reverser and self.drawer == "speed":
            rect = self.buttons.get("reverser_selector")
            if rect is not None:
                return {"reverser_position": self._reverser_position_from_y(event.pos[1], rect)}
        if event.type == pygame.MOUSEMOTION and self.dragging_lever and self.drawer == "motion":
            self._set_notch_from_y(event.pos[1], train)
            return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        self.pressed_button = next((key for key, rect in self.buttons.items()
                                    if self._button_hit(key, rect, event.pos)), None)
        if self.dragging_lever:
            self._set_notch_from_y(event.pos[1], train)
            return True

        for key, rect in list(self.buttons.items()):
            if not self._button_hit(key, rect, event.pos):
                continue
            if key.startswith("tab_"):
                name = key[4:]
                self.drawer = None if self.drawer == name else name
            elif key == "reverser_selector":
                self.dragging_reverser = True
                return {"reverser_position": self._reverser_position_from_y(event.pos[1], rect)}
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
            elif key == "reset_emergency":
                return {"reset_emergency": True}
            elif key == "play_announcement":
                if self.announcement_items:
                    item = self.announcement_items[self.announcement_index]
                    self.announcement_index = (self.announcement_index + 1) % len(self.announcement_items)
                    self._keep_announcement_visible()
                    return {"play_announcement": item}
            elif key == "announcement_up":
                self.announcement_index = max(0, self.announcement_index - 1)
                self._keep_announcement_visible()
            elif key == "announcement_down":
                self.announcement_index = min(
                    max(0, len(self.announcement_items) - 1),
                    self.announcement_index + 1,
                )
                self._keep_announcement_visible()
            elif key.startswith("announcement_item_"):
                self.announcement_index = int(key.rsplit("_", 1)[1])
                self._keep_announcement_visible()
            elif key == "lever":
                self.dragging_lever = True
                self._set_notch_from_y(event.pos[1], train)
            return True
        return False

    def _keep_announcement_visible(self):
        visible_rows = 6
        if self.announcement_index < self.announcement_scroll:
            self.announcement_scroll = self.announcement_index
        elif self.announcement_index >= self.announcement_scroll + visible_rows:
            self.announcement_scroll = self.announcement_index - visible_rows + 1

    @staticmethod
    def _reverser_position_from_y(y, rect):
        relative = (y - rect.top) / max(1, rect.height)
        if relative < 1.0 / 3.0:
            return 1
        if relative > 2.0 / 3.0:
            return -1
        return 0

    @staticmethod
    def _speed_band_color(value, current_limit, future_limit):
        if value > current_limit + 0.1:
            return (214, 65, 62)
        if future_limit < current_limit - 0.1 and value > future_limit + 0.1:
            return (221, 177, 60)
        return (128, 140, 145)

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
        top_y, card_h = 16, 88
        limit_width, gap = 72, 12
        map_width = max(240, min((width - 132) // 2, width - 122))
        limit_box = pygame.Rect(18, top_y, limit_width, card_h)
        pygame.draw.rect(surface, (22, 30, 36), limit_box, border_radius=12)
        pygame.draw.rect(surface, (73, 88, 94), limit_box, 1, border_radius=12)
        self._text(surface, "ЛИМИТ", (limit_box.x + 12, limit_box.y + 12), self.MUTED, self.tiny)

        direction = 1 if getattr(train, "direction", 1) >= 0 else -1
        current_limit = float(getattr(train, "current_speed_limit_mps", train.max_speed)) * 3.6
        saved_indication = getattr(train.als, "indication_kmh", 0.0)
        saved_blocks = getattr(train.als, "free_blocks_ahead", 0)
        samples = []
        for distance in range(0, int(self.window_distance) + 1, 35):
            position = float(train.position) + direction * distance
            position = max(0.0, min(float(line.path.total_length), position))
            limit, _ = line.block_indication(position, train)
            limit = min(90.0, float(limit), float(train.max_speed) * 3.6)
            if distance == 0:
                current_limit = min(current_limit, limit) if current_limit > 0 else limit
            samples.append((float(distance), limit))
        train.als.indication_kmh = saved_indication
        train.als.free_blocks_ahead = saved_blocks
        self._current_route_limit_kmh = current_limit

        limit_text = pygame.font.SysFont("arial", 32, bold=True).render(
            str(round(current_limit)), True, (230, 202, 104)
        )
        surface.blit(limit_text, limit_text.get_rect(center=(limit_box.centerx, limit_box.y + 52)))

        box = pygame.Rect((width - map_width) // 2, top_y, map_width, card_h)
        pygame.draw.rect(surface, (22, 30, 36), box, border_radius=12)
        pygame.draw.rect(surface, (73, 88, 94), box, 1, border_radius=12)
        self._text(surface, "ПУТЬ ВПЕРЁДИ", (box.x + 14, box.y + 8), self.MUTED, self.tiny)
        track_y, left, right = box.y + 52, box.x + 24, box.right - 14
        pygame.draw.line(surface, (67, 76, 81), (left, track_y), (right, track_y), 7)
        pygame.draw.line(surface, (36, 43, 48), (left, track_y), (right, track_y), 2)
        pygame.draw.line(surface, (240, 244, 242), (left, track_y - 15), (left, track_y + 15), 3)

        px_per_m = (right - left) / self.window_distance
        self._next_restriction = None
        previous_limit = samples[0][1] if samples else current_limit
        for distance, limit in samples[1:]:
            if limit < previous_limit - 0.1:
                x = int(left + distance * px_per_m)
                if self._next_restriction is None:
                    self._next_restriction = (distance, limit)
                pygame.draw.rect(surface, (132, 143, 148), (x - 2, track_y - 16, 5, 32))
            previous_limit = limit
        for station in line.stations:
            distance = (float(station.get("position", 0)) - float(train.position)) * direction
            if 0 <= distance <= self.window_distance:
                x = int(left + distance * px_per_m)
                pygame.draw.circle(surface, (184, 198, 200), (x, track_y), 3)

    def _draw_tabs(self, surface):
        _, height = surface.get_size()
        tabs = (("motion", "ХОД"), ("doors", "ДВЕРИ"),
                ("speed", "СКОРОСТЬ"), ("announcements", "ОБЪЯВЛЕНИЯ"))
        x0, gap, y = 18, 112, height - 76
        for index, (key, label) in enumerate(tabs):
            rect = pygame.Rect(x0 + index * gap, y, 48, 48)
            self._button(surface, f"tab_{key}", "", rect,
                         active=self.drawer == key,
                         color=self.TURQUOISE if self.drawer == key else None)
            text = self.small.render(label, True, self.TEXT)
            surface.blit(text, text.get_rect(midtop=(rect.centerx, rect.bottom + 2)))

    def _drawer_rect(self, surface, height=300, width=520):
        screen_width, screen_height = surface.get_size()
        rect = pygame.Rect(18, max(126, screen_height - height - 94),
                           min(width, screen_width - 36), height)
        pygame.draw.rect(surface, self.PANEL, rect, border_radius=14)
        pygame.draw.rect(surface, self.PANEL_EDGE, rect, 1, border_radius=14)
        return rect

    def _draw_motion(self, surface, train):
        panel = self._drawer_rect(surface, height=318)
        self._text(surface, "УПРАВЛЕНИЕ ХОДОМ", (panel.x + 18, panel.y + 12), self.TEXT, self.title)
        track = pygame.Rect(panel.x + 42, panel.y + 64, 12, 196)
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
                   (panel.x + 245, panel.y + 72), self.TEXT, self.font)
        self._text(surface, f"Скорость  {round(abs(train.speed) * 3.6)} км/ч",
                   (panel.x + 245, panel.y + 108), self.TEXT, self.font)

        red_rect = pygame.Rect(panel.x + 274, panel.y + 158, 56, 56)
        yellow_rect = pygame.Rect(panel.x + 392, panel.y + 158, 56, 56)
        self._button(surface, "reset_emergency", "", red_rect, color=self.RED)
        self._button(surface, "play_announcement", "", yellow_rect, color=self.YELLOW)
        red_label = self.small.render("СБРОС ЭКСТР.", True, self.TEXT)
        red_label2 = self.small.render("ТОРМОЗА", True, self.TEXT)
        yellow_label = self.small.render("ОБЪЯВЛЕНИЕ", True, self.TEXT)
        yellow_label2 = self.small.render("СТАНЦИИ", True, self.TEXT)
        surface.blit(red_label, red_label.get_rect(center=(red_rect.centerx, red_rect.bottom + 12)))
        surface.blit(red_label2, red_label2.get_rect(center=(red_rect.centerx, red_rect.bottom + 28)))
        surface.blit(yellow_label, yellow_label.get_rect(center=(yellow_rect.centerx, yellow_rect.bottom + 12)))
        surface.blit(yellow_label2, yellow_label2.get_rect(center=(yellow_rect.centerx, yellow_rect.bottom + 28)))

    def _draw_doors(self, surface, train, game):
        panel = self._drawer_rect(surface, height=300)
        self._text(surface, "УПРАВЛЕНИЕ ДВЕРЬМИ", (panel.x + 18, panel.y + 12), self.TEXT, self.title)
        controls = (
            ("left_side", "ВЫБОР", "ЛЕВЫХ", game.selected_door_side == "left", self.TURQUOISE),
            ("right_side", "ВЫБОР", "ПРАВЫХ", game.selected_door_side == "right", self.TURQUOISE),
            ("open_left", "ОТКРЫТЬ", "ЛЕВЫЕ", game.doors_open and game.selected_door_side == "left", None),
            ("open_right", "ОТКРЫТЬ", "ПРАВЫЕ", game.doors_open and game.selected_door_side == "right", None),
            ("close_doors", "ЗАКРЫТЬ", "ДВЕРИ", self.door_flash > 0, self.GREEN),
        )
        positions = ((panel.x + 58, panel.y + 112), (panel.x + 158, panel.y + 112),
                     (panel.x + 258, panel.y + 112), (panel.x + 358, panel.y + 112),
                     (panel.x + 458, panel.y + 112))
        for (key, line1, line2, active, color), (cx, cy) in zip(controls, positions):
            rect = pygame.Rect(cx - 28, cy - 28, 56, 56)
            self._button(surface, key, "", rect, active=active, color=color)
            for offset, label in ((40, line1), (56, line2)):
                text = self.small.render(label, True, self.TEXT)
                surface.blit(text, text.get_rect(center=(cx, cy + offset)))
        status = "ДВЕРИ ОТКРЫТЫ" if game.doors_open else "ДВЕРИ ЗАКРЫТЫ"
        self._text(surface, status, (panel.x + 22, panel.bottom - 30),
                   (117, 222, 171) if game.doors_open else self.MUTED, self.font)
        if abs(train.speed) >= 0.05:
            self._text(surface, "Открытие доступно только при остановке поезда",
                       (panel.x + 22, panel.bottom - 10), (225, 187, 105), self.tiny)

    def _build_announcement_items(self, line, game):
        items = []
        sounds = getattr(game.audio, "station_announcement_sounds", {})
        stations = line.stations
        for index, station in enumerate(stations, start=1):
            station_name = str(station.get("name", f"Станция {index}"))
            if "current" in sounds.get(index, {}):
                items.append({
                    "station_number": index,
                    "display_station_number": index,
                    "kind": "current",
                    "label": station_name,
                })

            # A departure from station N announces station N+1, so the
            # playback clip belongs to the next station, not the one shown.
            next_station_number = index + 1
            if (next_station_number <= len(stations)
                    and "next" in sounds.get(next_station_number, {})):
                items.append({
                    "station_number": next_station_number,
                    "display_station_number": index,
                    "kind": "next",
                    "label": f"{station_name} — отпр.",
                })
        self.announcement_items = items
        if items:
            self.announcement_index = max(0, min(self.announcement_index, len(items) - 1))
            self._keep_announcement_visible()
        else:
            self.announcement_index = self.announcement_scroll = 0

    def _draw_announcements(self, surface, line, game):
        panel = self._drawer_rect(surface, height=318, width=610)
        self._build_announcement_items(line, game)
        self._text(surface, "БОРТОВОЙ КОМПЬЮТЕР · ОБЪЯВЛЕНИЯ", (panel.x + 18, panel.y + 12),
                   self.TEXT, self.title)
        self._text(surface, "Выбранное объявление будет следующим", (panel.x + 18, panel.y + 40),
                   self.MUTED, self.small)
        list_rect = pygame.Rect(panel.x + 18, panel.y + 68, panel.width - 104, 6 * self.announcement_row_height)
        pygame.draw.rect(surface, (12, 19, 24), list_rect, border_radius=7)
        visible = 6
        for row in range(visible):
            index = self.announcement_scroll + row
            if index >= len(self.announcement_items):
                break
            item = self.announcement_items[index]
            row_rect = pygame.Rect(list_rect.x + 3, list_rect.y + row * self.announcement_row_height + 1,
                                   list_rect.width - 6, self.announcement_row_height - 2)
            selected = index == self.announcement_index
            color = (49, 112, 116) if selected else (31, 43, 50)
            pygame.draw.rect(surface, color, row_rect, border_radius=4)
            self.buttons[f"announcement_item_{index}"] = row_rect
            display_number = item.get("display_station_number", item["station_number"])
            label = f'{display_number:02d}. {item["label"]}'
            self._text(surface, label, (row_rect.x + 10, row_rect.y + 6),
                       self.TEXT if selected else self.MUTED, self.small)
        if not self.announcement_items:
            self._text(surface, "Для этой линии аудиофайлы объявлений не найдены",
                       (list_rect.x + 10, list_rect.y + 12), self.MUTED, self.small)

        arrow_x = list_rect.right + 12
        self._rect_button(surface, "announcement_up", "ВВЕРХ",
                          pygame.Rect(arrow_x, list_rect.y + 58, 70, 42))
        self._rect_button(surface, "announcement_down", "ВНИЗ",
                          pygame.Rect(arrow_x, list_rect.y + 112, 70, 42))
        if self.announcement_items:
            selected = self.announcement_items[self.announcement_index]
            self._text(surface, f'СЛЕДУЮЩЕЕ: {selected["label"]}',
                       (panel.x + 18, panel.bottom - 38), (230, 202, 104), self.small)

    def _draw_speedometer(self, surface, train, line):
        width, _ = surface.get_size()
        panel = self._drawer_rect(surface, height=318, width=520)
        panel.x = width - panel.width - 18
        pygame.draw.rect(surface, (5, 8, 11), panel, border_radius=14)
        pygame.draw.rect(surface, self.PANEL_EDGE, panel, 1, border_radius=14)
        self._text(surface, "СКОРОСТЕМЕР", (panel.x + 18, panel.y + 12), self.TEXT, self.title)

        # Three-position reverser: forward / neutral / reverse.
        selector_rect = pygame.Rect(panel.x + 28, panel.y + 78, 222, 184)
        self.buttons["reverser_selector"] = selector_rect
        pivot = (panel.x + 96, panel.y + 174)
        selector = max(-1, min(1, int(getattr(train, "reverser_position", 0) or 0)))
        detents = {
            1: (pivot[0] + 43, pivot[1] - 42),
            0: (pivot[0] + 49, pivot[1]),
            -1: (pivot[0] + 43, pivot[1] + 42),
        }
        endpoint = detents[selector]
        pygame.draw.line(surface, (72, 86, 92), detents[1], detents[-1], 8)
        for point in detents.values():
            pygame.draw.circle(surface, (183, 195, 198), point, 5)
        pygame.draw.line(surface, (205, 215, 217), pivot, endpoint, 9)
        pygame.draw.circle(surface, (48, 62, 68), pivot, 15)
        pygame.draw.circle(surface, (210, 221, 222), pivot, 9)
        pygame.draw.circle(surface, (239, 245, 245), endpoint, 10)
        selector_label = {1: "ВПЕРЁД", 0: "НЕЙТРАЛЬ", -1: "НАЗАД"}[selector]
        self._text(surface, selector_label, (panel.x + 154, panel.y + 164),
                   (230, 202, 104), self.font)
        self._text(surface, "РЕВЕРСОР", (panel.x + 46, panel.y + 82), self.MUTED, self.tiny)

        # The dial is kept to the right so the reverser remains clearly separate.
        center, radius = (panel.x + 388, panel.y + 174), 106
        pygame.draw.circle(surface, (11, 15, 18), center, radius + 12)
        pygame.draw.circle(surface, (83, 94, 99), center, radius + 6, 2)
        future = self._next_restriction
        current_limit = float(getattr(
            self, "_current_route_limit_kmh",
            float(getattr(train, "current_speed_limit_mps", train.max_speed)) * 3.6
        ))
        future_limit = future[1] if future else current_limit
        future_limit = min(current_limit, float(future_limit))
        for value in range(0, 91, 5):
            angle = math.radians(135 + value / 90 * 270)
            outer = (center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius)
            inner = (center[0] + math.cos(angle) * (radius - (13 if value % 10 == 0 else 7)),
                     center[1] + math.sin(angle) * (radius - (13 if value % 10 == 0 else 7)))
            color = self._speed_band_color(value, current_limit, future_limit)
            pygame.draw.line(surface, color, inner, outer, 3 if value % 10 == 0 else 2)
            if value % 10 == 0:
                tx = center[0] + math.cos(angle) * (radius - 30)
                ty = center[1] + math.sin(angle) * (radius - 30)
                label = self.small.render(str(value), True, self.TEXT)
                surface.blit(label, label.get_rect(center=(int(tx), int(ty))))
        speed = max(0.0, min(90.0, abs(float(train.speed)) * 3.6))
        angle = math.radians(135 + speed / 90 * 270)
        tip = (center[0] + math.cos(angle) * (radius - 42), center[1] + math.sin(angle) * (radius - 42))
        pygame.draw.line(surface, (177, 187, 191), center, tip, 4)
        pygame.draw.circle(surface, (195, 205, 208), center, 7)
        speed_text = self.title.render(f"{speed:.0f}", True, self.TEXT)
        surface.blit(speed_text, speed_text.get_rect(center=(center[0], center[1] + 35)))
        self._text(surface, "км/ч", (center[0] - 19, center[1] + 56), self.MUTED, self.tiny)
        self._text(surface, f"РАЗРЕШЕНО: {current_limit:.0f} км/ч",
                   (panel.x + 22, panel.bottom - 42), (226, 190, 88), self.font)
        if future is not None and future_limit < current_limit - 0.1:
            self._text(surface, f"СЛЕД. БЛОК: {future_limit:.0f} км/ч",
                       (panel.x + 250, panel.bottom - 42), self.YELLOW, self.small)

    def render(self, surface, line, train, game):
        self.buttons.clear()
        self._draw_route_map(surface, line, train)
        if self.drawer == "motion":
            self._draw_motion(surface, train)
        elif self.drawer == "doors":
            self._draw_doors(surface, train, game)
        elif self.drawer == "speed":
            self._draw_speedometer(surface, train, line)
        elif self.drawer == "announcements":
            self._draw_announcements(surface, line, game)
        self._draw_tabs(surface)
