"""Configurable keyboard controls for the train simulator."""
import pygame


class InputController:
    DEFAULT_KEYBINDS = {
        "emergency_brake": "space",
        "traction_up": "w",
        "traction_down": "s",
        "reverser_forward": "p",
        "reverser_reverse": "o",
        "parking_brake": "k",
        "reset_overspeed": "b",
        "select_left_door": "shift+a",
        "select_right_door": "shift+d",
        "open_left_door": "a",
        "open_right_door": "d",
        "close_doors": "v",
        "change_cab": "0",
        "station_announcer": "i",
        "route_left": "q",
        "route_right": "e",
        "camera_left": "left",
        "camera_right": "right",
    }

    ACTION_LABELS = {
        "emergency_brake": "Экстренное торможение",
        "traction_up": "Увеличить тягу",
        "traction_down": "Уменьшить тягу / торможение",
        "reverser_forward": "Реверсор вперёд",
        "reverser_reverse": "Реверсор назад",
        "parking_brake": "Стояночный тормоз",
        "reset_overspeed": "Сброс защиты скорости",
        "select_left_door": "Выбрать левую сторону дверей",
        "select_right_door": "Выбрать правую сторону дверей",
        "open_left_door": "Открыть левые двери",
        "open_right_door": "Открыть правые двери",
        "close_doors": "Закрыть двери",
        "change_cab": "Сменить кабину",
        "station_announcer": "Объявления станций",
        "route_left": "Запросить маршрут влево",
        "route_right": "Запросить маршрут вправо",
        "camera_left": "Камера влево",
        "camera_right": "Камера вправо",
    }

    def __init__(self, keybinds=None):
        self.emergency = False
        self.keybinds = dict(self.DEFAULT_KEYBINDS)
        if keybinds:
            self.keybinds.update({
                key: value for key, value in keybinds.items()
                if key in self.DEFAULT_KEYBINDS and isinstance(value, str)
            })

    def set_keybinds(self, keybinds):
        self.keybinds.update({
            key: value for key, value in keybinds.items()
            if key in self.DEFAULT_KEYBINDS and isinstance(value, str)
        })

    def matches(self, event, action):
        if event.type != pygame.KEYDOWN:
            return False
        binding = self.keybinds.get(action, self.DEFAULT_KEYBINDS[action]).lower()
        parts = binding.split("+")
        key_name = parts[-1]
        try:
            key_code = pygame.key.key_code(key_name)
        except (ValueError, pygame.error):
            return False
        if event.key != key_code:
            return False
        mods = getattr(event, "mod", pygame.key.get_mods())
        wants_shift = "shift" in parts[:-1]
        wants_ctrl = "ctrl" in parts[:-1] or "control" in parts[:-1]
        wants_alt = "alt" in parts[:-1]
        return (
            bool(mods & pygame.KMOD_SHIFT) == wants_shift
            and bool(mods & pygame.KMOD_CTRL) == wants_ctrl
            and bool(mods & pygame.KMOD_ALT) == wants_alt
        )

    def handle_event(self, event, train):
        if event.type == pygame.KEYDOWN:
            if self.matches(event, "emergency_brake"):
                self.emergency = True
            elif self.matches(event, "traction_up"):
                train.controller_notch = min(4, train.controller_notch + 1)
            elif self.matches(event, "traction_down"):
                train.controller_notch = max(-3, train.controller_notch - 1)
            elif self.matches(event, "reverser_forward"):
                if abs(train.speed) < 0.05 and hasattr(train, "reverser_position"):
                    train.reverser_position = min(1, train.reverser_position + 1)
            elif self.matches(event, "reverser_reverse"):
                if abs(train.speed) < 0.05 and hasattr(train, "reverser_position"):
                    train.reverser_position = max(-1, train.reverser_position - 1)
            elif self.matches(event, "parking_brake"):
                train.parking_brake_active = not train.parking_brake_active
            elif self.matches(event, "reset_overspeed"):
                if abs(train.speed) < 0.05 and train.controller_notch == -3:
                    train.overspeed_emergency_active = False
                    train.overspeed_timer = 0.0
        elif event.type == pygame.KEYUP and self.matches(event, "emergency_brake"):
            self.emergency = False

    def update(self, train, dt):
        train.manual_emergency_brake_active = self.emergency
