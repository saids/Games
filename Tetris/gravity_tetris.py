"""
Gravity Shift Tetris - A Revolutionary Tetris Concept
======================================================
A unique twist on classic Tetris where you can shift gravity in any direction!
Press arrow keys to move/rotate pieces, and use 1-4 to change gravity direction.
All placed blocks will shift when gravity changes, opening new strategic possibilities.

Controls:
- Left/Right: Move piece
- Up: Rotate piece
- Down: Soft drop
- Space: Hard drop
- 1: Gravity DOWN (default)
- 2: Gravity UP
- 3: Gravity LEFT
- 4: Gravity RIGHT
- P: Pause
- R: Restart (when game over)
- ESC: Quit
"""

import pygame
import random
import sys
from enum import Enum
from typing import List, Tuple, Optional
from dataclasses import dataclass
import math

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants
CELL_SIZE = 30
BOARD_WIDTH = 10
BOARD_HEIGHT = 20
SIDEBAR_WIDTH = 200
WINDOW_WIDTH = BOARD_WIDTH * CELL_SIZE + SIDEBAR_WIDTH
WINDOW_HEIGHT = BOARD_HEIGHT * CELL_SIZE

# Colors
COLORS = {
    'background': (15, 15, 35),
    'grid': (40, 40, 60),
    'text': (255, 255, 255),
    'shadow': (100, 100, 120),
    'I': (0, 240, 240),
    'O': (240, 240, 0),
    'T': (160, 0, 240),
    'S': (0, 240, 0),
    'Z': (240, 0, 0),
    'J': (0, 0, 240),
    'L': (240, 160, 0),
}

# Tetromino shapes (relative positions)
TETROMINOES = {
    'I': [(0, 0), (0, 1), (0, 2), (0, 3)],
    'O': [(0, 0), (1, 0), (0, 1), (1, 1)],
    'T': [(0, 0), (1, 0), (2, 0), (1, 1)],
    'S': [(1, 0), (2, 0), (0, 1), (1, 1)],
    'Z': [(0, 0), (1, 0), (1, 1), (2, 1)],
    'J': [(0, 0), (0, 1), (1, 1), (2, 1)],
    'L': [(2, 0), (0, 1), (1, 1), (2, 1)],
}


class Gravity(Enum):
    DOWN = (0, 1)
    UP = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


@dataclass
class Block:
    x: int
    y: int
    color: Tuple[int, int, int]


class Particle:
    def __init__(self, x: float, y: float, color: Tuple[int, int, int]):
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-5, -1)
        self.life = 1.0
        self.decay = random.uniform(0.02, 0.05)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # gravity
        self.life -= self.decay
        return self.life > 0

    def draw(self, screen: pygame.Surface):
        alpha = int(self.life * 255)
        color = (*self.color[:3], alpha)
        size = int(4 * self.life)
        if size > 0:
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (size, size), size)
            screen.blit(surf, (self.x - size, self.y - size))


class Tetromino:
    def __init__(self, shape_type: str):
        self.shape_type = shape_type
        self.color = COLORS[shape_type]
        self.blocks = [list(pos) for pos in TETROMINOES[shape_type]]
        self.x = BOARD_WIDTH // 2 - 1
        self.y = 0
        self.rotation = 0

    def get_positions(self) -> List[Tuple[int, int]]:
        return [(self.x + bx, self.y + by) for bx, by in self.blocks]

    def rotate(self, clockwise: bool = True):
        if self.shape_type == 'O':
            return  # O doesn't rotate

        # Find center of rotation
        cx = sum(b[0] for b in self.blocks) / 4
        cy = sum(b[1] for b in self.blocks) / 4

        new_blocks = []
        for bx, by in self.blocks:
            # Translate to origin
            tx, ty = bx - cx, by - cy
            # Rotate
            if clockwise:
                nx, ny = -ty, tx
            else:
                nx, ny = ty, -tx
            # Translate back
            new_blocks.append([round(nx + cx), round(ny + cy)])

        self.blocks = new_blocks
        self.rotation = (self.rotation + (1 if clockwise else -1)) % 4

    def copy(self) -> 'Tetromino':
        t = Tetromino(self.shape_type)
        t.blocks = [b[:] for b in self.blocks]
        t.x = self.x
        t.y = self.y
        t.rotation = self.rotation
        return t


class GravityTetris:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Gravity Shift Tetris")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 28)

        self.reset_game()

    def reset_game(self):
        self.board: List[List[Optional[Tuple[int, int, int]]]] = [
            [None for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)
        ]
        self.gravity = Gravity.DOWN
        self.current_piece: Optional[Tetromino] = None
        self.next_piece: Optional[Tetromino] = None
        self.held_piece: Optional[Tetromino] = None
        self.can_hold = True
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.game_over = False
        self.paused = False
        self.fall_time = 0
        self.fall_speed = 1000  # milliseconds
        self.gravity_shift_cooldown = 0
        self.particles: List[Particle] = []
        self.shake_offset = [0, 0]
        self.shake_time = 0
        self.gravity_shifting = False
        self.shift_animation_progress = 0

        self.spawn_piece()

    def spawn_piece(self):
        if self.next_piece:
            self.current_piece = self.next_piece
        else:
            self.current_piece = Tetromino(random.choice(list(TETROMINOES.keys())))

        self.next_piece = Tetromino(random.choice(list(TETROMINOES.keys())))
        self.current_piece.x = BOARD_WIDTH // 2 - 1
        self.current_piece.y = 0
        self.can_hold = True

        # Check game over
        if not self.is_valid_position(self.current_piece):
            self.game_over = True

    def is_valid_position(self, piece: Tetromino, offset_x: int = 0, offset_y: int = 0) -> bool:
        for bx, by in piece.blocks:
            x = piece.x + bx + offset_x
            y = piece.y + by + offset_y

            if x < 0 or x >= BOARD_WIDTH or y < 0 or y >= BOARD_HEIGHT:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False

        return True

    def lock_piece(self):
        if not self.current_piece:
            return

        for bx, by in self.current_piece.blocks:
            x = self.current_piece.x + bx
            y = self.current_piece.y + by
            if 0 <= y < BOARD_HEIGHT and 0 <= x < BOARD_WIDTH:
                self.board[y][x] = self.current_piece.color

        self.clear_lines()
        self.spawn_piece()

    def clear_lines(self):
        """Clear lines based on current gravity direction."""
        lines_to_clear = []

        if self.gravity in (Gravity.DOWN, Gravity.UP):
            # Check horizontal lines
            for y in range(BOARD_HEIGHT):
                if all(self.board[y][x] is not None for x in range(BOARD_WIDTH)):
                    lines_to_clear.append(('horizontal', y))
        else:
            # Check vertical lines
            for x in range(BOARD_WIDTH):
                if all(self.board[y][x] is not None for y in range(BOARD_HEIGHT)):
                    lines_to_clear.append(('vertical', x))

        if lines_to_clear:
            self.create_clear_particles(lines_to_clear)
            self.shake_time = 10

            for line_type, idx in lines_to_clear:
                if line_type == 'horizontal':
                    # Clear horizontal line and shift based on gravity
                    for x in range(BOARD_WIDTH):
                        self.board[idx][x] = None
                else:
                    # Clear vertical line
                    for y in range(BOARD_HEIGHT):
                        self.board[y][idx] = None

            # Apply gravity after clearing
            self.apply_gravity_to_board()

            num_lines = len(lines_to_clear)
            self.lines_cleared += num_lines
            self.score += [0, 100, 300, 500, 800][min(num_lines, 4)] * self.level

            # Level up
            self.level = self.lines_cleared // 10 + 1
            self.fall_speed = max(100, 1000 - (self.level - 1) * 80)

    def create_clear_particles(self, lines: List[Tuple[str, int]]):
        for line_type, idx in lines:
            if line_type == 'horizontal':
                for x in range(BOARD_WIDTH):
                    color = self.board[idx][x]
                    if color:
                        px = x * CELL_SIZE + CELL_SIZE // 2
                        py = idx * CELL_SIZE + CELL_SIZE // 2
                        for _ in range(5):
                            self.particles.append(Particle(px, py, color))
            else:
                for y in range(BOARD_HEIGHT):
                    color = self.board[y][idx]
                    if color:
                        px = idx * CELL_SIZE + CELL_SIZE // 2
                        py = y * CELL_SIZE + CELL_SIZE // 2
                        for _ in range(5):
                            self.particles.append(Particle(px, py, color))

    def apply_gravity_to_board(self):
        """Make all blocks fall in the current gravity direction."""
        dx, dy = self.gravity.value
        changed = True

        while changed:
            changed = False

            if self.gravity == Gravity.DOWN:
                for y in range(BOARD_HEIGHT - 2, -1, -1):
                    for x in range(BOARD_WIDTH):
                        if self.board[y][x] and not self.board[y + 1][x]:
                            self.board[y + 1][x] = self.board[y][x]
                            self.board[y][x] = None
                            changed = True

            elif self.gravity == Gravity.UP:
                for y in range(1, BOARD_HEIGHT):
                    for x in range(BOARD_WIDTH):
                        if self.board[y][x] and not self.board[y - 1][x]:
                            self.board[y - 1][x] = self.board[y][x]
                            self.board[y][x] = None
                            changed = True

            elif self.gravity == Gravity.LEFT:
                for x in range(1, BOARD_WIDTH):
                    for y in range(BOARD_HEIGHT):
                        if self.board[y][x] and not self.board[y][x - 1]:
                            self.board[y][x - 1] = self.board[y][x]
                            self.board[y][x] = None
                            changed = True

            elif self.gravity == Gravity.RIGHT:
                for x in range(BOARD_WIDTH - 2, -1, -1):
                    for y in range(BOARD_HEIGHT):
                        if self.board[y][x] and not self.board[y][x + 1]:
                            self.board[y][x + 1] = self.board[y][x]
                            self.board[y][x] = None
                            changed = True

    def shift_gravity(self, new_gravity: Gravity):
        """Change gravity direction and apply it to all blocks."""
        if new_gravity == self.gravity or self.gravity_shift_cooldown > 0:
            return

        self.gravity = new_gravity
        self.gravity_shift_cooldown = 500  # milliseconds
        self.gravity_shifting = True
        self.shift_animation_progress = 0
        self.shake_time = 15

        # Lock current piece if it exists
        if self.current_piece:
            self.lock_piece()

        # Apply gravity to all blocks
        self.apply_gravity_to_board()

        # Clear any lines formed
        self.clear_lines()

        # Spawn new piece
        if not self.game_over:
            self.spawn_piece()

    def move_piece(self, dx: int, dy: int) -> bool:
        if not self.current_piece:
            return False

        if self.is_valid_position(self.current_piece, dx, dy):
            self.current_piece.x += dx
            self.current_piece.y += dy
            return True
        return False

    def rotate_piece(self):
        if not self.current_piece:
            return

        original_blocks = [b[:] for b in self.current_piece.blocks]
        self.current_piece.rotate()

        # Wall kick attempts
        kicks = [(0, 0), (-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0)]
        for kx, ky in kicks:
            if self.is_valid_position(self.current_piece, kx, ky):
                self.current_piece.x += kx
                self.current_piece.y += ky
                return

        # Revert if no valid position
        self.current_piece.blocks = original_blocks

    def hard_drop(self):
        if not self.current_piece:
            return

        drop_distance = 0
        while self.is_valid_position(self.current_piece, 0, 1):
            self.current_piece.y += 1
            drop_distance += 1

        self.score += drop_distance * 2
        self.lock_piece()

    def get_ghost_position(self) -> int:
        if not self.current_piece:
            return 0

        ghost_y = 0
        while self.is_valid_position(self.current_piece, 0, ghost_y + 1):
            ghost_y += 1
        return ghost_y

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False

                if self.game_over:
                    if event.key == pygame.K_r:
                        self.reset_game()
                    continue

                if event.key == pygame.K_p:
                    self.paused = not self.paused
                    continue

                if self.paused:
                    continue

                # Gravity shifts (1-4 keys)
                if event.key == pygame.K_1:
                    self.shift_gravity(Gravity.DOWN)
                elif event.key == pygame.K_2:
                    self.shift_gravity(Gravity.UP)
                elif event.key == pygame.K_3:
                    self.shift_gravity(Gravity.LEFT)
                elif event.key == pygame.K_4:
                    self.shift_gravity(Gravity.RIGHT)

                # Movement
                elif event.key == pygame.K_LEFT:
                    self.move_piece(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    self.move_piece(1, 0)
                elif event.key == pygame.K_DOWN:
                    if self.move_piece(0, 1):
                        self.score += 1
                elif event.key == pygame.K_UP:
                    self.rotate_piece()
                elif event.key == pygame.K_SPACE:
                    self.hard_drop()

        return True

    def update(self, dt: int):
        if self.game_over or self.paused:
            return

        # Update cooldowns
        if self.gravity_shift_cooldown > 0:
            self.gravity_shift_cooldown -= dt

        # Update animation
        if self.gravity_shifting:
            self.shift_animation_progress += dt / 200
            if self.shift_animation_progress >= 1:
                self.gravity_shifting = False

        # Update shake
        if self.shake_time > 0:
            self.shake_offset = [random.randint(-3, 3), random.randint(-3, 3)]
            self.shake_time -= 1
        else:
            self.shake_offset = [0, 0]

        # Update particles
        self.particles = [p for p in self.particles if p.update()]

        # Natural falling
        self.fall_time += dt
        if self.fall_time >= self.fall_speed:
            self.fall_time = 0
            if not self.move_piece(0, 1):
                self.lock_piece()

    def draw_block(self, x: int, y: int, color: Tuple[int, int, int], alpha: float = 1.0):
        """Draw a single block with 3D effect."""
        px = x * CELL_SIZE + self.shake_offset[0]
        py = y * CELL_SIZE + self.shake_offset[1]

        # Main color
        rect = pygame.Rect(px, py, CELL_SIZE - 1, CELL_SIZE - 1)

        if alpha < 1.0:
            surf = pygame.Surface((CELL_SIZE - 1, CELL_SIZE - 1), pygame.SRCALPHA)
            c = (*color, int(alpha * 255))
            pygame.draw.rect(surf, c, (0, 0, CELL_SIZE - 1, CELL_SIZE - 1))
            self.screen.blit(surf, (px, py))
        else:
            pygame.draw.rect(self.screen, color, rect)

            # Highlight
            highlight = tuple(min(255, c + 50) for c in color)
            pygame.draw.line(self.screen, highlight, (px, py), (px + CELL_SIZE - 2, py), 2)
            pygame.draw.line(self.screen, highlight, (px, py), (px, py + CELL_SIZE - 2), 2)

            # Shadow
            shadow = tuple(max(0, c - 50) for c in color)
            pygame.draw.line(self.screen, shadow, (px + CELL_SIZE - 2, py),
                           (px + CELL_SIZE - 2, py + CELL_SIZE - 2), 2)
            pygame.draw.line(self.screen, shadow, (px, py + CELL_SIZE - 2),
                           (px + CELL_SIZE - 2, py + CELL_SIZE - 2), 2)

    def draw_board(self):
        # Draw grid
        for y in range(BOARD_HEIGHT):
            for x in range(BOARD_WIDTH):
                px = x * CELL_SIZE + self.shake_offset[0]
                py = y * CELL_SIZE + self.shake_offset[1]
                pygame.draw.rect(self.screen, COLORS['grid'],
                               (px, py, CELL_SIZE, CELL_SIZE), 1)

        # Draw placed blocks
        for y in range(BOARD_HEIGHT):
            for x in range(BOARD_WIDTH):
                if self.board[y][x]:
                    self.draw_block(x, y, self.board[y][x])

        # Draw ghost piece
        if self.current_piece and not self.gravity_shifting:
            ghost_y = self.get_ghost_position()
            for bx, by in self.current_piece.blocks:
                x = self.current_piece.x + bx
                y = self.current_piece.y + by + ghost_y
                if 0 <= y < BOARD_HEIGHT and 0 <= x < BOARD_WIDTH:
                    self.draw_block(x, y, self.current_piece.color, 0.3)

        # Draw current piece
        if self.current_piece and not self.gravity_shifting:
            for bx, by in self.current_piece.blocks:
                x = self.current_piece.x + bx
                y = self.current_piece.y + by
                if 0 <= y < BOARD_HEIGHT and 0 <= x < BOARD_WIDTH:
                    self.draw_block(x, y, self.current_piece.color)

    def draw_sidebar(self):
        sidebar_x = BOARD_WIDTH * CELL_SIZE + 10

        # Title
        title = self.title_font.render("GRAVITY TETRIS", True, COLORS['text'])
        self.screen.blit(title, (sidebar_x, 10))

        # Score
        score_text = self.font.render(f"Score: {self.score}", True, COLORS['text'])
        self.screen.blit(score_text, (sidebar_x, 50))

        # Level
        level_text = self.font.render(f"Level: {self.level}", True, COLORS['text'])
        self.screen.blit(level_text, (sidebar_x, 85))

        # Lines
        lines_text = self.font.render(f"Lines: {self.lines_cleared}", True, COLORS['text'])
        self.screen.blit(lines_text, (sidebar_x, 120))

        # Current gravity indicator
        gravity_names = {
            Gravity.DOWN: "DOWN (1)",
            Gravity.UP: "UP (2)",
            Gravity.LEFT: "LEFT (3)",
            Gravity.RIGHT: "RIGHT (4)"
        }
        gravity_text = self.small_font.render(f"Gravity:", True, COLORS['text'])
        self.screen.blit(gravity_text, (sidebar_x, 165))

        grav_value = self.small_font.render(gravity_names[self.gravity], True, (100, 200, 255))
        self.screen.blit(grav_value, (sidebar_x, 185))

        # Draw gravity arrow
        arrow_center = (sidebar_x + 90, 225)
        arrow_size = 20
        dx, dy = self.gravity.value
        end_x = arrow_center[0] + dx * arrow_size
        end_y = arrow_center[1] + dy * arrow_size
        pygame.draw.circle(self.screen, (60, 60, 80), arrow_center, 25)
        pygame.draw.line(self.screen, (100, 200, 255), arrow_center, (end_x, end_y), 3)

        # Cooldown indicator
        if self.gravity_shift_cooldown > 0:
            cooldown_text = self.small_font.render("Shifting...", True, (255, 200, 100))
            self.screen.blit(cooldown_text, (sidebar_x, 260))

        # Next piece
        next_text = self.small_font.render("Next:", True, COLORS['text'])
        self.screen.blit(next_text, (sidebar_x, 300))

        if self.next_piece:
            for bx, by in TETROMINOES[self.next_piece.shape_type]:
                px = sidebar_x + 20 + bx * 20
                py = 330 + by * 20
                pygame.draw.rect(self.screen, self.next_piece.color,
                               (px, py, 18, 18))

        # Controls help
        controls_y = 430
        controls = [
            "Controls:",
            "Arrows: Move/Rotate",
            "Space: Hard Drop",
            "1-4: Shift Gravity",
            "P: Pause",
        ]
        for i, text in enumerate(controls):
            color = COLORS['text'] if i == 0 else (150, 150, 170)
            ctrl_text = self.small_font.render(text, True, color)
            self.screen.blit(ctrl_text, (sidebar_x, controls_y + i * 22))

    def draw_overlay(self):
        if self.paused:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))

            pause_text = self.font.render("PAUSED", True, COLORS['text'])
            rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
            self.screen.blit(pause_text, rect)

        if self.game_over:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            go_text = self.font.render("GAME OVER", True, (255, 100, 100))
            rect = go_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30))
            self.screen.blit(go_text, rect)

            score_text = self.font.render(f"Final Score: {self.score}", True, COLORS['text'])
            rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 10))
            self.screen.blit(score_text, rect)

            restart_text = self.small_font.render("Press R to restart", True, (200, 200, 200))
            rect = restart_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50))
            self.screen.blit(restart_text, rect)

    def draw(self):
        self.screen.fill(COLORS['background'])
        self.draw_board()
        self.draw_sidebar()

        # Draw particles
        for particle in self.particles:
            particle.draw(self.screen)

        self.draw_overlay()
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60)
            running = self.handle_input()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = GravityTetris()
    game.run()
