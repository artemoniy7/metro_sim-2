"""In-game pause overlay and settings screen."""
from pathlib import Path
import pygame


class PauseMenu:
    BG = (13, 18, 25)
    PANEL = (25, 33, 43)
    PANEL2 = (36, 48, 61)
    TEXT = (240, 243, 247)
    MUTED = (151, 164, 179)
    ACCENT = (218, 38, 55)
    BORDER = (65, 80, 97)

    def __init__(self):
        pygame.font.init()
        font_dir = Path(__file__).resolve().parent.parent / "assets" / "ui" / "fonts"
        self.title_font = self._font(font_dir / "IBMPlexSans-Bold.ttf", 34, True)
        self.button_font = self._font(font_dir / "IBMPlexSans-Medium.ttf", 20)
        self.body_font = self._font(font_dir / "IBMPlexSans-Regular.ttf", 17)
        self.page = "pause"
        self.volume = 70
        self.fullscreen = True
        self.buttons = {}

    @staticmethod
    def _font(path, size, bold=False):
        try:
            return pygame.font.Font(str(path), size)
        except (OSError, pygame.error):
            return pygame.font.SysFont("arial", size, bold=bold)

    def _button(self, surface, key, label, rect, primary=False, danger=False):
        self.buttons[key] = rect
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        color = self.ACCENT if primary else ((105, 38, 48) if danger else
                                               (self.PANEL2 if hovered else (30, 40, 52)))
        pygame.draw.rect(surface, color, rect, border_radius=9)
        pygame.draw.rect(surface, self.BORDER, rect, 1, border_radius=9)
        text = self.button_font.render(label, True, self.TEXT)
        surface.blit(text, text.get_rect(center=rect.center))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.page == "settings":
                self.page = "pause"
                return None
            return "resume"
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
            else:
                if key == "volume_down":
                    self.volume = max(0, self.volume - 10)
                    pygame.mixer.set_volume(self.volume / 100)
                elif key == "volume_up":
                    self.volume = min(100, self.volume + 10)
                    pygame.mixer.set_volume(self.volume / 100)
                elif key == "fullscreen":
                    self.fullscreen = not self.fullscreen
                    return "toggle_fullscreen"
                elif key == "back":
                    self.page = "pause"
            return None
        return None

    def render(self, surface):
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((3, 7, 12, 178))
        surface.blit(overlay, (0, 0))
        self.buttons.clear()

        panel_width = min(460, width - 36)
        panel_height = 360 if self.page == "pause" else 390
        panel = pygame.Rect(0, 0, panel_width, panel_height)
        panel.center = (width // 2, height // 2)

        shadow = panel.move(0, 8)
        pygame.draw.rect(surface, (5, 8, 13), shadow, border_radius=18)
        pygame.draw.rect(surface, self.PANEL, panel, border_radius=18)
        pygame.draw.rect(surface, self.BORDER, panel, 1, border_radius=18)
        pygame.draw.rect(surface, self.ACCENT, (panel.x + 28, panel.y + 28, 5, 36),
                         border_radius=2)

        if self.page == "pause":
            title = self.title_font.render("ПАУЗА", True, self.TEXT)
            surface.blit(title, (panel.x + 48, panel.y + 25))
            subtitle = self.body_font.render("Игра приостановлена", True, self.MUTED)
            surface.blit(subtitle, (panel.x + 30, panel.y + 78))
            button_width = panel.width - 60
            x = panel.x + 30
            self._button(surface, "continue", "Продолжить",
                         pygame.Rect(x, panel.y + 125, button_width, 52), primary=True)
            self._button(surface, "settings", "Настройки",
                         pygame.Rect(x, panel.y + 190, button_width, 48))
            self._button(surface, "main_menu", "Выйти в меню",
                         pygame.Rect(x, panel.y + 251, button_width, 48), danger=True)
            hint = self.body_font.render("ESC — вернуться в игру", True, self.MUTED)
            surface.blit(hint, hint.get_rect(center=(panel.centerx, panel.bottom - 23)))
        else:
            title = self.title_font.render("НАСТРОЙКИ", True, self.TEXT)
            surface.blit(title, (panel.x + 48, panel.y + 25))
            label = self.body_font.render(f"Громкость звука: {self.volume}%", True, self.MUTED)
            surface.blit(label, (panel.x + 30, panel.y + 100))
            self._button(surface, "volume_down", "−",
                         pygame.Rect(panel.x + 30, panel.y + 135, 64, 44))
            self._button(surface, "volume_up", "+",
                         pygame.Rect(panel.x + 108, panel.y + 135, 64, 44))
            self._button(surface, "fullscreen",
                         "Полный экран: " + ("Да" if self.fullscreen else "Нет"),
                         pygame.Rect(panel.x + 30, panel.y + 205, panel.width - 60, 46))
            self._button(surface, "back", "Назад",
                         pygame.Rect(panel.x + 30, panel.bottom - 72, panel.width - 60, 44),
                         primary=True)
