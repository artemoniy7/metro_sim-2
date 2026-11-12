"""In-game pause overlay, remappable controls and audio settings."""
import json
from pathlib import Path
import pygame

from systems.input import InputController


class PauseMenu:
    PANEL = (25, 33, 43)
    PANEL2 = (36, 48, 61)
    TEXT = (240, 243, 247)
    MUTED = (151, 164, 179)
    ACCENT = (218, 38, 55)
    BORDER = (65, 80, 97)
    SETTINGS_PATH = Path(__file__).resolve().parent.parent / "saves" / "settings.json"
    AUDIO_GROUPS = {
        "master": "Общая громкость",
        "train": "Поезд (двигатель, тормоза, двери)",
        "environment": "Окружение (стыки, станция)",
        "announcements": "Объявления",
    }

    def __init__(self):
        pygame.font.init()
        font_dir = Path(__file__).resolve().parent.parent / "assets" / "ui" / "fonts"
        self.title_font = self._font(font_dir / "IBMPlexSans-Bold.ttf", 31, True)
        self.button_font = self._font(font_dir / "IBMPlexSans-Medium.ttf", 18)
        self.body_font = self._font(font_dir / "IBMPlexSans-Regular.ttf", 16)
        self.small_font = self._font(font_dir / "IBMPlexSans-Regular.ttf", 13)
        self.page = "pause"
        self.buttons = {}
        self.capture_action = None
        self.scroll_offset = 0
        self.notice = ""
        self.audio = None
        self.keybinds = dict(InputController.DEFAULT_KEYBINDS)
        self.volume_groups = {"master": 100, "train": 100, "environment": 100, "announcements": 100}
        self._load_settings()

    @staticmethod
    def _font(path, size, bold=False):
        try:
            return pygame.font.Font(str(path), size)
        except (OSError, pygame.error):
            return pygame.font.SysFont("arial", size, bold=bold)

    def _load_settings(self):
        try:
            data = json.loads(self.SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return
        stored_keys = data.get("keybinds", {})
        if isinstance(stored_keys, dict):
            for action in self.keybinds:
                value = stored_keys.get(action)
                if isinstance(value, str) and value:
                    self.keybinds[action] = value
        stored_volumes = data.get("volume_groups", {})
        if isinstance(stored_volumes, dict):
            for group in self.volume_groups:
                try:
                    self.volume_groups[group] = max(0, min(100, int(stored_volumes.get(group, 100))))
                except (TypeError, ValueError):
                    pass

    def _save_settings(self):
        self.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"keybinds": self.keybinds, "volume_groups": self.volume_groups}
        self.SETTINGS_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def set_audio(self, audio):
        self.audio = audio
        if audio is not None:
            for group, value in self.volume_groups.items():
                audio.set_volume_group(group, value / 100.0)

    def _button(self, surface, key, label, rect, primary=False, danger=False, compact=False):
        self.buttons[key] = rect
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        color = self.ACCENT if primary else ((105, 38, 48) if danger else
                                               (self.PANEL2 if hovered else (30, 40, 52)))
        pygame.draw.rect(surface, color, rect, border_radius=8)
        pygame.draw.rect(surface, self.BORDER, rect, 1, border_radius=8)
        font = self.small_font if compact else self.button_font
        text = font.render(label, True, self.TEXT)
        surface.blit(text, text.get_rect(center=rect.center))

    def handle_event(self, event, audio=None):
        if audio is not None and audio is not self.audio:
            self.set_audio(audio)

        if self.capture_action:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.capture_action = None
                    self.notice = "Переназначение отменено"
                    return None
                key_name = pygame.key.name(event.key).lower()
                mods = getattr(event, "mod", pygame.key.get_mods())
                modifiers = []
                if mods & pygame.KMOD_CTRL:
                    modifiers.append("ctrl")
                if mods & pygame.KMOD_ALT:
                    modifiers.append("alt")
                if mods & pygame.KMOD_SHIFT and key_name not in ("left shift", "right shift"):
                    modifiers.append("shift")
                binding = "+".join(modifiers + [key_name])
                duplicate = next(
                    (name for name, value in self.keybinds.items()
                     if name != self.capture_action and value == binding),
                    None,
                )
                if duplicate:
                    self.notice = "Эта клавиша уже назначена"
                else:
                    self.keybinds[self.capture_action] = binding
                    self._save_settings()
                    self.notice = "Назначение сохранено"
                self.capture_action = None
            return None

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.page == "settings":
                self.page = "pause"
            elif self.page in ("controls", "audio"):
                self.page = "settings"
                self.scroll_offset = 0
            else:
                return "resume"
            return None

        if event.type == pygame.MOUSEWHEEL:
            if self.page == "controls":
                max_offset = max(0, len(self.keybinds) - 10)
                self.scroll_offset = max(0, min(max_offset, self.scroll_offset - event.y))
            return None

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        for key, rect in list(self.buttons.items()):
            if not rect.collidepoint(event.pos):
                continue
            if self.page == "pause":
                if key == "continue":
                    return "resume"
                if key == "settings":
                    self.page = "settings"
                elif key == "main_menu":
                    return "main_menu"
            elif self.page == "settings":
                if key == "controls":
                    self.page = "controls"
                    self.scroll_offset = 0
                elif key == "audio":
                    self.page = "audio"
                elif key == "back":
                    self.page = "pause"
            elif self.page == "controls":
                if key.startswith("bind_"):
                    self.capture_action = key[5:]
                    self.notice = "Нажми новую клавишу или ESC для отмены"
                elif key == "controls_back":
                    self.page = "settings"
            elif self.page == "audio":
                if key.startswith("volume_"):
                    _, group, direction = key.split("_")
                    delta = 10 if direction == "up" else -10
                    self.volume_groups[group] = max(0, min(100, self.volume_groups[group] + delta))
                    if self.audio is not None:
                        self.audio.set_volume_group(group, self.volume_groups[group] / 100.0)
                    self._save_settings()
                elif key == "audio_back":
                    self.page = "settings"
            return None
        return None

    def render(self, surface):
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((3, 7, 12, 178))
        surface.blit(overlay, (0, 0))
        self.buttons.clear()

        if self.page == "pause":
            self._render_pause(surface)
        elif self.page == "settings":
            self._render_settings(surface)
        elif self.page == "controls":
            self._render_controls(surface)
        elif self.page == "audio":
            self._render_audio(surface)

    def _panel(self, surface, width, height):
        panel = pygame.Rect(0, 0, min(width, surface.get_width() - 32),
                            min(height, surface.get_height() - 28))
        panel.center = surface.get_rect().center
        pygame.draw.rect(surface, (5, 8, 13), panel.move(0, 7), border_radius=17)
        pygame.draw.rect(surface, self.PANEL, panel, border_radius=17)
        pygame.draw.rect(surface, self.BORDER, panel, 1, border_radius=17)
        pygame.draw.rect(surface, self.ACCENT, (panel.x + 25, panel.y + 24, 5, 34),
                         border_radius=2)
        return panel

    def _heading(self, surface, panel, title, subtitle=None):
        surface.blit(self.title_font.render(title, True, self.TEXT), (panel.x + 43, panel.y + 20))
        if subtitle:
            surface.blit(self.small_font.render(subtitle, True, self.MUTED),
                         (panel.x + 28, panel.y + 64))

    def _render_pause(self, surface):
        panel = self._panel(surface, 460, 360)
        self._heading(surface, panel, "ПАУЗА", "Игра приостановлена")
        x, bw = panel.x + 30, panel.width - 60
        self._button(surface, "continue", "Продолжить", pygame.Rect(x, panel.y + 116, bw, 52), primary=True)
        self._button(surface, "settings", "Настройки", pygame.Rect(x, panel.y + 181, bw, 48))
        self._button(surface, "main_menu", "Выйти в меню", pygame.Rect(x, panel.y + 242, bw, 48), danger=True)
        hint = self.small_font.render("ESC — вернуться в игру", True, self.MUTED)
        surface.blit(hint, hint.get_rect(center=(panel.centerx, panel.bottom - 18)))

    def _render_settings(self, surface):
        panel = self._panel(surface, 500, 350)
        self._heading(surface, panel, "НАСТРОЙКИ", "Настрой управление и звук")
        x, bw = panel.x + 30, panel.width - 60
        self._button(surface, "controls", "Переназначить клавиши", pygame.Rect(x, panel.y + 112, bw, 54))
        self._button(surface, "audio", "Громкость звука", pygame.Rect(x, panel.y + 180, bw, 54))
        self._button(surface, "back", "Назад", pygame.Rect(x, panel.y + 255, bw, 44), primary=True)

    def _render_controls(self, surface):
        panel = self._panel(surface, 760, 620)
        self._heading(surface, panel, "УПРАВЛЕНИЕ", "Нажми «Изменить», затем новую клавишу. ESC — пауза; колесо мыши — зум камеры.")
        actions = list(self.keybinds.items())
        visible = actions[self.scroll_offset:self.scroll_offset + 10]
        row_top = panel.y + 92
        for index, (action, binding) in enumerate(visible):
            y = row_top + index * 39
            label = InputController.ACTION_LABELS.get(action, action)
            surface.blit(self.small_font.render(label, True, self.TEXT), (panel.x + 28, y + 10))
            btn = pygame.Rect(panel.right - 170, y + 2, 140, 32)
            changing = self.capture_action == action
            text = "Нажми клавишу…" if changing else binding.upper()
            self._button(surface, f"bind_{action}", text, btn, primary=changing, compact=True)
        if self.notice:
            surface.blit(self.small_font.render(self.notice, True, self.ACCENT),
                         (panel.x + 28, panel.bottom - 61))
        self._button(surface, "controls_back", "Назад",
                     pygame.Rect(panel.x + 28, panel.bottom - 43, panel.width - 56, 34), primary=True, compact=True)

    def _render_audio(self, surface):
        panel = self._panel(surface, 650, 500)
        self._heading(surface, panel, "ГРОМКОСТЬ", "Настройки сохраняются автоматически")
        for index, (group, label) in enumerate(self.AUDIO_GROUPS.items()):
            y = panel.y + 112 + index * 72
            surface.blit(self.body_font.render(label, True, self.TEXT), (panel.x + 30, y))
            value = self.volume_groups[group]
            surface.blit(self.button_font.render(f"{value}%", True, self.TEXT),
                         (panel.right - 140, y - 2))
            self._button(surface, f"volume_{group}_down", "−",
                         pygame.Rect(panel.right - 220, y + 27, 54, 34), compact=True)
            self._button(surface, f"volume_{group}_up", "+",
                         pygame.Rect(panel.right - 154, y + 27, 54, 34), compact=True)
            bar = pygame.Rect(panel.x + 30, y + 32, panel.width - 270, 22)
            pygame.draw.rect(surface, (15, 21, 29), bar, border_radius=6)
            fill = bar.copy()
            fill.width = int(bar.width * value / 100)
            if fill.width:
                pygame.draw.rect(surface, self.ACCENT, fill, border_radius=6)
        self._button(surface, "audio_back", "Назад",
                     pygame.Rect(panel.x + 30, panel.bottom - 60, panel.width - 60, 40), primary=True)
