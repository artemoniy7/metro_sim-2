"""Entry point for Metro Sim."""
import pygame
from settings import WINDOW_SIZE, WINDOW_TITLE, FPS
from systems.menu import MainMenu
from systems.pause_menu import PauseMenu


def create_selected_game(menu):
    from core.game import Game
    line_meta, line_path, line_data = menu.selected_line
    train_path, train_data = menu.selected_train
    stations = line_data.get("stations", [])
    end_index = min(menu.end_index, len(stations) - 1)
    end_position = float(stations[end_index].get("position", line_data.get("total_length_m", 0)))
    return Game(
        line_file=line_path.name,
        train_file=train_path.name,
        start_position=menu.selected_start_position,
        end_position=end_position,
    )


def main():
    pygame.init()
    desktop = pygame.display.Info()
    screen = pygame.display.set_mode((desktop.current_w, desktop.current_h), pygame.NOFRAME)
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    menu = MainMenu(WINDOW_SIZE)
    pause_menu = PauseMenu()
    game = None
    scene = "menu"
    paused = False
    running = True

    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if scene == "menu":
                action = menu.handle_event(event)
                if action == "quit":
                    running = False
                elif action == "start":
                    game = create_selected_game(menu)
                    game.controls.set_keybinds(pause_menu.keybinds)
                    pause_menu.set_audio(game.audio)
                    scene = "game"
                    paused = False
            elif game is not None:
                if paused:
                    action = pause_menu.handle_event(event, game.audio)
                    game.controls.set_keybinds(pause_menu.keybinds)
                    if action == "resume":
                        paused = False
                        pygame.mixer.unpause()
                    elif action == "main_menu":
                        paused = False
                        pygame.mixer.stop()
                        scene = "menu"
                        menu.page = "home"
                        game = None
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    paused = True
                    pause_menu.page = "pause"
                    pygame.mixer.pause()
                else:
                    game.handle_event(event)

        if scene == "menu":
            menu.update(dt)
            menu.render(screen)
        elif game is not None:
            if not paused:
                game.update(dt)
            game.render(screen)
            if paused:
                pause_menu.render(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
