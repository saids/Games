#!/usr/bin/env python3
"""
Flappy Bird Clone - A pygame implementation
Full screen game with scoring and graphics
"""

import pygame
import random
import math
import sys
from enum import Enum


class GameState(Enum):
    MENU = 1
    PLAYING = 2
    GAME_OVER = 3


class Bird:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.velocity = 0
        self.gravity = 0.5
        self.jump_strength = -10
        self.width = 50
        self.height = 35
        self.angle = 0
        self.animation_time = 0
        self.wing_up = True

    def jump(self):
        self.velocity = self.jump_strength

    def update(self):
        self.velocity += self.gravity
        self.y += self.velocity

        # Calculate rotation based on velocity
        self.angle = max(-30, min(45, -self.velocity * 3))

        # Wing animation
        self.animation_time += 1
        if self.animation_time >= 5:
            self.wing_up = not self.wing_up
            self.animation_time = 0

    def draw(self, screen):
        # Draw bird body (ellipse)
        body_color = (255, 220, 50)  # Yellow
        body_rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2,
                                self.width, self.height)

        # Create a surface for the bird to apply rotation
        bird_surface = pygame.Surface((self.width + 20, self.height + 20), pygame.SRCALPHA)
        center = (bird_surface.get_width() // 2, bird_surface.get_height() // 2)

        # Body
        pygame.draw.ellipse(bird_surface, body_color,
                          (10, 10, self.width, self.height))
        pygame.draw.ellipse(bird_surface, (200, 170, 40),
                          (10, 10, self.width, self.height), 2)

        # Eye
        eye_x = center[0] + 10
        eye_y = center[1] - 5
        pygame.draw.circle(bird_surface, (255, 255, 255), (eye_x, eye_y), 8)
        pygame.draw.circle(bird_surface, (0, 0, 0), (eye_x + 2, eye_y), 4)

        # Beak
        beak_points = [
            (center[0] + self.width // 2 - 5, center[1]),
            (center[0] + self.width // 2 + 15, center[1] + 3),
            (center[0] + self.width // 2 - 5, center[1] + 8)
        ]
        pygame.draw.polygon(bird_surface, (255, 150, 50), beak_points)

        # Wing
        wing_y_offset = -5 if self.wing_up else 5
        wing_points = [
            (center[0] - 5, center[1]),
            (center[0] - 15, center[1] + wing_y_offset + 15),
            (center[0] + 10, center[1] + 10)
        ]
        pygame.draw.polygon(bird_surface, (230, 190, 40), wing_points)
        pygame.draw.polygon(bird_surface, (180, 140, 30), wing_points, 2)

        # Rotate and blit
        rotated = pygame.transform.rotate(bird_surface, self.angle)
        rect = rotated.get_rect(center=(self.x, self.y))
        screen.blit(rotated, rect)

    def get_rect(self):
        return pygame.Rect(self.x - self.width // 2 + 5,
                          self.y - self.height // 2 + 5,
                          self.width - 10, self.height - 10)


class Pipe:
    def __init__(self, x, screen_height, gap=200):
        self.x = x
        self.width = 80
        self.gap = gap
        self.screen_height = screen_height
        self.gap_y = random.randint(150, screen_height - 150 - gap)
        self.passed = False
        self.speed = 5

    def update(self):
        self.x -= self.speed

    def draw(self, screen):
        pipe_color = (50, 200, 50)
        pipe_dark = (30, 150, 30)
        pipe_light = (80, 230, 80)

        # Top pipe
        top_rect = pygame.Rect(self.x, 0, self.width, self.gap_y)
        pygame.draw.rect(screen, pipe_color, top_rect)
        pygame.draw.rect(screen, pipe_dark, top_rect, 3)

        # Top pipe cap
        cap_height = 30
        cap_rect = pygame.Rect(self.x - 5, self.gap_y - cap_height,
                               self.width + 10, cap_height)
        pygame.draw.rect(screen, pipe_color, cap_rect)
        pygame.draw.rect(screen, pipe_dark, cap_rect, 3)

        # Highlight on top pipe
        pygame.draw.line(screen, pipe_light,
                        (self.x + 5, 0), (self.x + 5, self.gap_y - cap_height), 4)

        # Bottom pipe
        bottom_y = self.gap_y + self.gap
        bottom_rect = pygame.Rect(self.x, bottom_y, self.width,
                                 self.screen_height - bottom_y)
        pygame.draw.rect(screen, pipe_color, bottom_rect)
        pygame.draw.rect(screen, pipe_dark, bottom_rect, 3)

        # Bottom pipe cap
        bottom_cap_rect = pygame.Rect(self.x - 5, bottom_y,
                                      self.width + 10, cap_height)
        pygame.draw.rect(screen, pipe_color, bottom_cap_rect)
        pygame.draw.rect(screen, pipe_dark, bottom_cap_rect, 3)

        # Highlight on bottom pipe
        pygame.draw.line(screen, pipe_light,
                        (self.x + 5, bottom_y + cap_height),
                        (self.x + 5, self.screen_height), 4)

    def get_rects(self):
        top_rect = pygame.Rect(self.x, 0, self.width, self.gap_y)
        bottom_rect = pygame.Rect(self.x, self.gap_y + self.gap,
                                 self.width, self.screen_height - self.gap_y - self.gap)
        return [top_rect, bottom_rect]

    def is_off_screen(self):
        return self.x + self.width < 0


class Cloud:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.speed = 1 + random.random()

    def update(self, screen_width):
        self.x -= self.speed
        if self.x + self.size * 3 < 0:
            self.x = screen_width + random.randint(50, 200)
            self.y = random.randint(50, 200)

    def draw(self, screen):
        color = (255, 255, 255)
        # Draw fluffy cloud with multiple circles
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(screen, color, (int(self.x + self.size), int(self.y - self.size // 2)),
                          int(self.size * 0.8))
        pygame.draw.circle(screen, color, (int(self.x + self.size * 1.5), int(self.y)),
                          int(self.size * 0.9))
        pygame.draw.circle(screen, color, (int(self.x + self.size * 0.5), int(self.y + self.size // 3)),
                          int(self.size * 0.7))


class Ground:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.height = 100
        self.y = screen_height - self.height
        self.offset = 0
        self.speed = 5

    def update(self):
        self.offset = (self.offset + self.speed) % 50

    def draw(self, screen):
        # Ground base
        ground_color = (222, 184, 135)  # Tan/sand color
        pygame.draw.rect(screen, ground_color,
                        (0, self.y, self.screen_width, self.height))

        # Grass on top
        grass_color = (100, 200, 100)
        grass_dark = (80, 160, 80)
        pygame.draw.rect(screen, grass_color,
                        (0, self.y, self.screen_width, 20))

        # Grass detail pattern
        for i in range(-50, self.screen_width + 50, 25):
            x = i - self.offset
            points = [
                (x, self.y + 20),
                (x + 12, self.y),
                (x + 25, self.y + 20)
            ]
            pygame.draw.polygon(screen, grass_dark, points)

        # Ground texture lines
        for i in range(3):
            y = self.y + 30 + i * 25
            pygame.draw.line(screen, (190, 160, 120),
                           (0, y), (self.screen_width, y), 2)


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, count=10):
        for _ in range(count):
            self.particles.append({
                'x': x,
                'y': y,
                'vx': random.uniform(-5, 5),
                'vy': random.uniform(-8, -2),
                'life': random.randint(20, 40),
                'color': random.choice([
                    (255, 220, 50),
                    (255, 200, 100),
                    (255, 255, 200)
                ])
            })

    def update(self):
        for p in self.particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.3  # Gravity
            p['life'] -= 1
            if p['life'] <= 0:
                self.particles.remove(p)

    def draw(self, screen):
        for p in self.particles:
            alpha = min(255, p['life'] * 10)
            size = max(1, p['life'] // 10)
            pygame.draw.circle(screen, p['color'],
                             (int(p['x']), int(p['y'])), size)


class FlappyBirdGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        # Set up full screen
        info = pygame.display.Info()
        self.screen_width = info.current_w
        self.screen_height = info.current_h
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height),
                                               pygame.FULLSCREEN)
        pygame.display.set_caption("Flappy Bird")

        self.clock = pygame.time.Clock()
        self.fps = 60

        # Initialize fonts
        self.title_font = pygame.font.Font(None, 120)
        self.score_font = pygame.font.Font(None, 80)
        self.menu_font = pygame.font.Font(None, 50)

        # Game objects
        self.bird = None
        self.pipes = []
        self.clouds = []
        self.ground = None
        self.particles = None

        # Game state
        self.state = GameState.MENU
        self.score = 0
        self.high_score = 0
        self.pipe_spawn_timer = 0
        self.pipe_spawn_interval = 90  # frames

        # Create sounds (synthetic beeps)
        self.create_sounds()

        self.reset_game()

    def create_sounds(self):
        """Create simple synthetic sounds"""
        try:
            # Jump sound
            sample_rate = 22050
            duration = 0.1
            t = [i / sample_rate for i in range(int(sample_rate * duration))]

            # Simple beep for jump
            jump_samples = []
            for i in t:
                value = int(127 * math.sin(2 * math.pi * 600 * i) * (1 - i / duration))
                jump_samples.append(value)

            jump_array = bytes([(s + 128) & 0xff for s in jump_samples])
            self.jump_sound = pygame.mixer.Sound(buffer=jump_array)
            self.jump_sound.set_volume(0.3)

            # Score sound
            score_samples = []
            for i in t:
                value = int(127 * math.sin(2 * math.pi * 880 * i) * (1 - i / duration))
                score_samples.append(value)

            score_array = bytes([(s + 128) & 0xff for s in score_samples])
            self.score_sound = pygame.mixer.Sound(buffer=score_array)
            self.score_sound.set_volume(0.3)

            # Hit sound
            duration = 0.2
            t = [i / sample_rate for i in range(int(sample_rate * duration))]
            hit_samples = []
            for i in t:
                freq = 200 * (1 - i / duration)
                value = int(127 * math.sin(2 * math.pi * freq * i) * (1 - i / duration))
                hit_samples.append(value)

            hit_array = bytes([(s + 128) & 0xff for s in hit_samples])
            self.hit_sound = pygame.mixer.Sound(buffer=hit_array)
            self.hit_sound.set_volume(0.4)

            self.sounds_enabled = True
        except Exception:
            self.sounds_enabled = False

    def reset_game(self):
        self.bird = Bird(self.screen_width // 4, self.screen_height // 2)
        self.pipes = []
        self.ground = Ground(self.screen_width, self.screen_height)
        self.particles = ParticleSystem()
        self.score = 0
        self.pipe_spawn_timer = 0

        # Create clouds
        self.clouds = []
        for i in range(5):
            x = random.randint(0, self.screen_width)
            y = random.randint(50, 200)
            size = random.randint(30, 60)
            self.clouds.append(Cloud(x, y, size))

    def spawn_pipe(self):
        gap = max(150, 200 - self.score * 2)  # Gap decreases with score
        pipe = Pipe(self.screen_width + 50, self.screen_height - self.ground.height, gap)
        pipe.speed = min(8, 5 + self.score * 0.1)  # Speed increases with score
        self.pipes.append(pipe)

    def check_collision(self):
        bird_rect = self.bird.get_rect()

        # Check ground collision
        if self.bird.y + self.bird.height // 2 >= self.ground.y:
            return True

        # Check ceiling collision
        if self.bird.y - self.bird.height // 2 <= 0:
            return True

        # Check pipe collision
        for pipe in self.pipes:
            for rect in pipe.get_rects():
                if bird_rect.colliderect(rect):
                    return True

        return False

    def draw_background(self):
        # Sky gradient
        for y in range(self.screen_height):
            ratio = y / self.screen_height
            r = int(135 + (200 - 135) * ratio)
            g = int(206 + (230 - 206) * ratio)
            b = int(235 + (255 - 235) * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (self.screen_width, y))

        # Draw clouds
        for cloud in self.clouds:
            cloud.draw(self.screen)

    def draw_score(self):
        # Draw score with shadow
        score_text = str(self.score)
        shadow = self.score_font.render(score_text, True, (0, 0, 0))
        text = self.score_font.render(score_text, True, (255, 255, 255))

        x = self.screen_width // 2 - text.get_width() // 2
        y = 50

        self.screen.blit(shadow, (x + 3, y + 3))
        self.screen.blit(text, (x, y))

    def draw_menu(self):
        self.draw_background()

        # Draw floating bird animation
        menu_bird_y = self.screen_height // 2 - 100 + math.sin(pygame.time.get_ticks() / 200) * 20
        menu_bird = Bird(self.screen_width // 2, menu_bird_y)
        menu_bird.animation_time = pygame.time.get_ticks() // 100
        menu_bird.wing_up = (pygame.time.get_ticks() // 150) % 2 == 0
        menu_bird.draw(self.screen)

        # Title with shadow
        title_shadow = self.title_font.render("FLAPPY BIRD", True, (0, 0, 0))
        title_text = self.title_font.render("FLAPPY BIRD", True, (255, 220, 50))
        title_x = self.screen_width // 2 - title_text.get_width() // 2
        title_y = 100
        self.screen.blit(title_shadow, (title_x + 4, title_y + 4))
        self.screen.blit(title_text, (title_x, title_y))

        # Instructions
        inst_text = self.menu_font.render("Press SPACE or CLICK to start", True, (50, 50, 50))
        inst_x = self.screen_width // 2 - inst_text.get_width() // 2
        inst_y = self.screen_height // 2 + 100
        self.screen.blit(inst_text, (inst_x, inst_y))

        # High score
        if self.high_score > 0:
            hs_text = self.menu_font.render(f"High Score: {self.high_score}", True, (100, 100, 100))
            hs_x = self.screen_width // 2 - hs_text.get_width() // 2
            hs_y = self.screen_height // 2 + 160
            self.screen.blit(hs_text, (hs_x, hs_y))

        # Exit instruction
        exit_text = self.menu_font.render("Press ESC to exit", True, (100, 100, 100))
        exit_x = self.screen_width // 2 - exit_text.get_width() // 2
        exit_y = self.screen_height - 80
        self.screen.blit(exit_text, (exit_x, exit_y))

        self.ground.draw(self.screen)

    def draw_game_over(self):
        # Darken screen
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))

        # Game Over text
        go_shadow = self.title_font.render("GAME OVER", True, (100, 0, 0))
        go_text = self.title_font.render("GAME OVER", True, (255, 50, 50))
        go_x = self.screen_width // 2 - go_text.get_width() // 2
        go_y = self.screen_height // 3
        self.screen.blit(go_shadow, (go_x + 4, go_y + 4))
        self.screen.blit(go_text, (go_x, go_y))

        # Final score
        score_text = self.score_font.render(f"Score: {self.score}", True, (255, 255, 255))
        score_x = self.screen_width // 2 - score_text.get_width() // 2
        score_y = self.screen_height // 2
        self.screen.blit(score_text, (score_x, score_y))

        # High score
        hs_color = (255, 215, 0) if self.score >= self.high_score else (200, 200, 200)
        hs_text = self.score_font.render(f"Best: {self.high_score}", True, hs_color)
        hs_x = self.screen_width // 2 - hs_text.get_width() // 2
        hs_y = self.screen_height // 2 + 70
        self.screen.blit(hs_text, (hs_x, hs_y))

        # New high score indicator
        if self.score >= self.high_score and self.score > 0:
            new_hs = self.menu_font.render("NEW HIGH SCORE!", True, (255, 215, 0))
            new_x = self.screen_width // 2 - new_hs.get_width() // 2
            new_y = self.screen_height // 2 + 140
            self.screen.blit(new_hs, (new_x, new_y))

        # Restart instruction
        restart_text = self.menu_font.render("Press SPACE to restart", True, (200, 200, 200))
        restart_x = self.screen_width // 2 - restart_text.get_width() // 2
        restart_y = self.screen_height // 2 + 200
        self.screen.blit(restart_text, (restart_x, restart_y))

    def update_game(self):
        # Update bird
        self.bird.update()

        # Update ground
        self.ground.update()

        # Update clouds
        for cloud in self.clouds:
            cloud.update(self.screen_width)

        # Update particles
        self.particles.update()

        # Spawn pipes
        self.pipe_spawn_timer += 1
        if self.pipe_spawn_timer >= self.pipe_spawn_interval:
            self.spawn_pipe()
            self.pipe_spawn_timer = 0

        # Update pipes
        for pipe in self.pipes[:]:
            pipe.update()

            # Check if bird passed pipe
            if not pipe.passed and pipe.x + pipe.width < self.bird.x:
                pipe.passed = True
                self.score += 1
                self.particles.emit(self.bird.x, self.bird.y, 15)
                if self.sounds_enabled:
                    self.score_sound.play()

            # Remove off-screen pipes
            if pipe.is_off_screen():
                self.pipes.remove(pipe)

        # Check collision
        if self.check_collision():
            self.state = GameState.GAME_OVER
            if self.score > self.high_score:
                self.high_score = self.score
            if self.sounds_enabled:
                self.hit_sound.play()

    def draw_game(self):
        self.draw_background()

        # Draw pipes
        for pipe in self.pipes:
            pipe.draw(self.screen)

        # Draw ground
        self.ground.draw(self.screen)

        # Draw particles
        self.particles.draw(self.screen)

        # Draw bird
        self.bird.draw(self.screen)

        # Draw score
        self.draw_score()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.MENU:
                        return False
                    else:
                        self.state = GameState.MENU
                        self.reset_game()

                if event.key == pygame.K_SPACE:
                    if self.state == GameState.MENU:
                        self.state = GameState.PLAYING
                        self.reset_game()
                    elif self.state == GameState.PLAYING:
                        self.bird.jump()
                        if self.sounds_enabled:
                            self.jump_sound.play()
                    elif self.state == GameState.GAME_OVER:
                        self.state = GameState.PLAYING
                        self.reset_game()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == GameState.MENU:
                    self.state = GameState.PLAYING
                    self.reset_game()
                elif self.state == GameState.PLAYING:
                    self.bird.jump()
                    if self.sounds_enabled:
                        self.jump_sound.play()
                elif self.state == GameState.GAME_OVER:
                    self.state = GameState.PLAYING
                    self.reset_game()

        return True

    def run(self):
        running = True

        while running:
            running = self.handle_events()

            if self.state == GameState.MENU:
                self.draw_menu()
            elif self.state == GameState.PLAYING:
                self.update_game()
                self.draw_game()
            elif self.state == GameState.GAME_OVER:
                self.draw_game()
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(self.fps)

        pygame.quit()
        sys.exit()


def main():
    game = FlappyBirdGame()
    game.run()


if __name__ == "__main__":
    main()
