"""Keyboard input for train controller, reverser and safety controls."""
import pygame


class InputController:
    def __init__(self):
        self.emergency = False

    def handle_event(self, event, train):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.emergency = True
            elif event.key == pygame.K_w:
                train.controller_notch = min(4, train.controller_notch + 1)
            elif event.key == pygame.K_s:
                train.controller_notch = max(-3, train.controller_notch - 1)
            elif event.key in (pygame.K_p, pygame.K_o):
                # P moves the reverser toward forward; O toward reverse.
                # The selector has three positions: reverse, neutral, forward.
                if abs(train.speed) < 0.05 and hasattr(train, "reverser_position"):
                    step = 1 if event.key == pygame.K_p else -1
                    train.reverser_position = max(-1, min(1, train.reverser_position + step))
            elif event.key == pygame.K_k:
                train.parking_brake_active = not train.parking_brake_active
            elif event.key == pygame.K_b:
                # Reset the overspeed trip only after stopping, selecting T3,
                # and acknowledging vigilance with B.
                if abs(train.speed) < 0.05 and train.controller_notch == -3:
                    train.overspeed_emergency_active = False
                    train.overspeed_timer = 0.0
        elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            self.emergency = False

    def update(self, train, dt):
        train.manual_emergency_brake_active = self.emergency
