"""
Gravity Shift Tetris - 3D Edition
==================================
A unique Tetris variant where you can shift gravity in any direction!
Features a fully 3D environment with textured blocks, depth effects,
perspective lighting, and fullscreen support.

Controls:
- Left/Right: Move piece
- Up: Rotate piece
- Down: Soft drop
- Space: Hard drop
- 1: Gravity DOWN (default)
- 2: Gravity UP
- 3: Gravity LEFT
- 4: Gravity RIGHT
- F11 / F: Toggle Fullscreen
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

pygame.init()
pygame.mixer.init()

# Base logical dimensions
CELL_SIZE = 34
BOARD_WIDTH = 10
BOARD_HEIGHT = 20
SIDEBAR_WIDTH = 220

BASE_WIDTH = BOARD_WIDTH * CELL_SIZE + SIDEBAR_WIDTH
BASE_HEIGHT = BOARD_HEIGHT * CELL_SIZE

# Depth / 3D perspective constants
DEPTH_OFFSET_X = 8   # isometric x shift
DEPTH_OFFSET_Y = 5   # isometric y shift

# Colors
COLORS = {
    'background': (8, 8, 22),
    'bg_grid':    (22, 22, 44),
    'grid':       (35, 35, 60),
    'grid_bright':(55, 55, 90),
    'text':       (230, 230, 255),
    'text_dim':   (140, 140, 170),
    'accent':     (80, 160, 255),
    'shadow':     (5, 5, 15),
    # Tetromino face colors
    'I': (0, 220, 220),
    'O': (230, 230, 0),
    'T': (180, 0, 240),
    'S': (0, 210, 60),
    'Z': (240, 50, 50),
    'J': (50, 80, 240),
    'L': (240, 150, 0),
}

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
    DOWN  = (0, 1)
    UP    = (0, -1)
    LEFT  = (-1, 0)
    RIGHT = (1, 0)


@dataclass
class Block:
    x: int
    y: int
    color: Tuple[int, int, int]


# ---------------------------------------------------------------------------
# Particle system
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x: float, y: float, color: Tuple[int, int, int]):
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-6, -1)
        self.life = 1.0
        self.decay = random.uniform(0.018, 0.045)
        self.size = random.uniform(3, 6)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.25
        self.life -= self.decay
        return self.life > 0

    def draw(self, screen: pygame.Surface):
        alpha = int(self.life * 255)
        size = max(1, int(self.size * self.life))
        surf = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color[:3], alpha), (size + 1, size + 1), size)
        screen.blit(surf, (int(self.x) - size - 1, int(self.y) - size - 1))


# ---------------------------------------------------------------------------
# Glow / bloom helper
# ---------------------------------------------------------------------------
def draw_glow(surface: pygame.Surface, color: Tuple[int, int, int],
              rect: pygame.Rect, radius: int = 6):
    """Draw a soft glow around a rectangle."""
    for r in range(radius, 0, -1):
        alpha = int(60 * (1 - r / radius))
        c = (*color[:3], alpha)
        glow_surf = pygame.Surface(
            (rect.width + r * 2, rect.height + r * 2), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, c,
                         (0, 0, rect.width + r * 2, rect.height + r * 2),
                         border_radius=r)
        surface.blit(glow_surf, (rect.x - r, rect.y - r))


# ---------------------------------------------------------------------------
# 3-D block renderer
# ---------------------------------------------------------------------------
def draw_block_3d(surface: pygame.Surface,
                  px: int, py: int,
                  color: Tuple[int, int, int],
                  cell: int = CELL_SIZE,
                  alpha: float = 1.0,
                  glow: bool = False):
    """
    Draw a single block with:
      - isometric top face
      - right depth face
      - front face with inner bevel + specular highlight
    """
    dx = DEPTH_OFFSET_X
    dy = DEPTH_OFFSET_Y

    r, g, b = color[0], color[1], color[2]

    face_color  = (r, g, b)
    top_color   = (min(255, int(r * 1.40)), min(255, int(g * 1.40)), min(255, int(b * 1.40)))
    right_color = (max(0, int(r * 0.55)),   max(0, int(g * 0.55)),   max(0, int(b * 0.55)))
    inner_hi    = (min(255, int(r * 1.60)), min(255, int(g * 1.60)), min(255, int(b * 1.60)))
    inner_sh    = (max(0, int(r * 0.40)),   max(0, int(g * 0.40)),   max(0, int(b * 0.40)))

    front = pygame.Rect(px + dx, py + dy, cell - 1, cell - 1)

    if alpha < 1.0:
        a_val = int(alpha * 160)
        ghost_surf = pygame.Surface((cell + dx, cell + dy), pygame.SRCALPHA)
        pygame.draw.rect(ghost_surf, (*face_color, a_val),
                         (dx, dy, cell - 1, cell - 1))
        pygame.draw.line(ghost_surf, (*inner_hi, a_val),
                         (dx, dy), (dx + cell - 2, dy), 1)
        pygame.draw.line(ghost_surf, (*inner_hi, a_val),
                         (dx, dy), (dx, dy + cell - 2), 1)
        surface.blit(ghost_surf, (px, py))
        return

    # Top face (parallelogram)
    top_pts = [
        (px,               py),
        (px + cell - 1,    py),
        (px + cell - 1 + dx, py + dy),
        (px + dx,          py + dy),
    ]
    pygame.draw.polygon(surface, top_color, top_pts)
    pygame.draw.polygon(surface, inner_hi,  top_pts, 1)

    # Right depth face (parallelogram)
    right_pts = [
        (px + cell - 1,        py),
        (px + cell - 1,        py + cell - 1),
        (px + cell - 1 + dx,   py + cell - 1 + dy),
        (px + cell - 1 + dx,   py + dy),
    ]
    pygame.draw.polygon(surface, right_color, right_pts)
    pygame.draw.polygon(surface, inner_sh,    right_pts, 1)

    # Front face
    pygame.draw.rect(surface, face_color, front)

    # Inner bevel
    bevel = 3
    pygame.draw.line(surface, inner_hi,
                     (front.left, front.top), (front.right, front.top), bevel)
    pygame.draw.line(surface, inner_hi,
                     (front.left, front.top), (front.left, front.bottom), bevel)
    pygame.draw.line(surface, inner_sh,
                     (front.right, front.top), (front.right, front.bottom), bevel)
    pygame.draw.line(surface, inner_sh,
                     (front.left, front.bottom), (front.right, front.bottom), bevel)

    # Specular highlight
    spec_size = max(3, cell // 6)
    spec_surf = pygame.Surface((cell, cell), pygame.SRCALPHA)
    spec_pts = [
        (bevel + 1,              bevel + 1),
        (bevel + spec_size,      bevel + 1),
        (bevel + 1,              bevel + spec_size),
    ]
    pygame.draw.polygon(spec_surf, (255, 255, 255, 120), spec_pts)
    surface.blit(spec_surf, (front.left, front.top))

    if glow:
        draw_glow(surface, face_color, front, radius=5)


# ---------------------------------------------------------------------------
# Tetromino
# ---------------------------------------------------------------------------
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
            return
        cx = sum(b[0] for b in self.blocks) / 4
        cy = sum(b[1] for b in self.blocks) / 4
        new_blocks = []
        for bx, by in self.blocks:
            tx, ty = bx - cx, by - cy
            if clockwise:
                nx, ny = -ty, tx
            else:
                nx, ny = ty, -tx
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


# ---------------------------------------------------------------------------
# Main game class
# ---------------------------------------------------------------------------
class GravityTetris:
    def __init__(self):
        self.fullscreen = False
        self.screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT))
        pygame.display.set_caption("Gravity Shift Tetris 3D")

        self.clock = pygame.time.Clock()
        self.font       = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 28)
        self.large_font = pygame.font.Font(None, 54)

        self._build_starfield()
        self.reset_game()

    # ------------------------------------------------------------------
    # Screen helpers
    # ------------------------------------------------------------------
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT))

    @property
    def win_w(self) -> int:
        return self.screen.get_width()

    @property
    def win_h(self) -> int:
        return self.screen.get_height()

    @property
    def board_offset_x(self) -> int:
        total_w = BOARD_WIDTH * CELL_SIZE + DEPTH_OFFSET_X + SIDEBAR_WIDTH
        return max(0, (self.win_w - total_w) // 2)

    @property
    def board_offset_y(self) -> int:
        total_h = BOARD_HEIGHT * CELL_SIZE + DEPTH_OFFSET_Y
        return max(0, (self.win_h - total_h) // 2)

    # ------------------------------------------------------------------
    # Starfield
    # ------------------------------------------------------------------
    def _build_starfield(self):
        self.stars = []
        for _ in range(200):
            self.stars.append({
                'x':       random.randint(0, 1920),
                'y':       random.randint(0, 1080),
                'r':       random.uniform(0.5, 2.2),
                'bright':  random.randint(120, 255),
                'twinkle': random.uniform(0, math.pi * 2),
                'speed':   random.uniform(0.02, 0.09),
            })

    def _draw_background(self):
        self.screen.fill(COLORS['background'])

        # Animated stars
        for s in self.stars:
            s['twinkle'] += s['speed']
            br = int(s['bright'] * (0.5 + 0.5 * math.sin(s['twinkle'])))
            c  = (br, br, min(255, br + 40))
            sx = int(s['x'] * self.win_w / 1920)
            sy = int(s['y'] * self.win_h / 1080)
            r  = max(1, int(s['r']))
            pygame.draw.circle(self.screen, c, (sx, sy), r)

        # Perspective floor grid (vanishing-point lines)
        vp_x = self.win_w // 2
        grid_c = (24, 24, 52)
        n_lines = 16
        for i in range(n_lines + 1):
            sx = int(i * self.win_w / n_lines)
            pygame.draw.line(self.screen, grid_c, (sx, self.win_h), (vp_x, 0), 1)
        for row in range(9):
            t_row = row / 9
            yw = int(self.win_h * (1 - t_row ** 1.7))
            hw = int(vp_x * (1 - t_row))
            pygame.draw.line(self.screen, grid_c,
                             (vp_x - hw, yw), (vp_x + hw, yw), 1)

    # ------------------------------------------------------------------
    # Game state
    # ------------------------------------------------------------------
    def reset_game(self):
        self.board: List[List[Optional[Tuple[int, int, int]]]] = [
            [None] * BOARD_WIDTH for _ in range(BOARD_HEIGHT)
        ]
        self.gravity = Gravity.DOWN
        self.current_piece: Optional[Tetromino] = None
        self.next_piece:    Optional[Tetromino] = None
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.game_over = False
        self.paused = False
        self.fall_time = 0
        self.fall_speed = 1000
        self.gravity_shift_cooldown = 0
        self.particles: List[Particle] = []
        self.shake_offset = [0, 0]
        self.shake_time = 0
        self.gravity_shifting = False
        self.shift_animation_progress = 0
        self.time_ms = 0
        self.spawn_piece()

    def spawn_piece(self):
        if self.next_piece:
            self.current_piece = self.next_piece
        else:
            self.current_piece = Tetromino(random.choice(list(TETROMINOES.keys())))
        self.next_piece = Tetromino(random.choice(list(TETROMINOES.keys())))
        self.current_piece.x = BOARD_WIDTH // 2 - 1
        self.current_piece.y = 0
        if not self.is_valid_position(self.current_piece):
            self.game_over = True

    def is_valid_position(self, piece: Tetromino,
                           offset_x: int = 0, offset_y: int = 0) -> bool:
        for bx, by in piece.blocks:
            x = piece.x + bx + offset_x
            y = piece.y + by + offset_y
            if x < 0 or x >= BOARD_WIDTH or y < 0 or y >= BOARD_HEIGHT:
                return False
            if self.board[y][x] is not None:
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
        lines_to_clear = []
        if self.gravity in (Gravity.DOWN, Gravity.UP):
            for y in range(BOARD_HEIGHT):
                if all(self.board[y][x] is not None for x in range(BOARD_WIDTH)):
                    lines_to_clear.append(('horizontal', y))
        else:
            for x in range(BOARD_WIDTH):
                if all(self.board[y][x] is not None for y in range(BOARD_HEIGHT)):
                    lines_to_clear.append(('vertical', x))

        if lines_to_clear:
            self.create_clear_particles(lines_to_clear)
            self.shake_time = 12
            for line_type, idx in lines_to_clear:
                if line_type == 'horizontal':
                    for x in range(BOARD_WIDTH):
                        self.board[idx][x] = None
                else:
                    for y in range(BOARD_HEIGHT):
                        self.board[y][idx] = None
            self.apply_gravity_to_board()
            num_lines = len(lines_to_clear)
            self.lines_cleared += num_lines
            self.score += [0, 100, 300, 500, 800][min(num_lines, 4)] * self.level
            self.level = self.lines_cleared // 10 + 1
            self.fall_speed = max(100, 1000 - (self.level - 1) * 80)

    def create_clear_particles(self, lines: List[Tuple[str, int]]):
        ox = self.board_offset_x + self.shake_offset[0]
        oy = self.board_offset_y + self.shake_offset[1]
        for line_type, idx in lines:
            if line_type == 'horizontal':
                for x in range(BOARD_WIDTH):
                    color = self.board[idx][x]
                    if color:
                        px = ox + x * CELL_SIZE + DEPTH_OFFSET_X + CELL_SIZE // 2
                        py = oy + idx * CELL_SIZE + DEPTH_OFFSET_Y + CELL_SIZE // 2
                        for _ in range(6):
                            self.particles.append(Particle(px, py, color))
            else:
                for y in range(BOARD_HEIGHT):
                    color = self.board[y][idx]
                    if color:
                        px = ox + idx * CELL_SIZE + DEPTH_OFFSET_X + CELL_SIZE // 2
                        py = oy + y  * CELL_SIZE + DEPTH_OFFSET_Y + CELL_SIZE // 2
                        for _ in range(6):
                            self.particles.append(Particle(px, py, color))

    def apply_gravity_to_board(self):
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
        if new_gravity == self.gravity or self.gravity_shift_cooldown > 0:
            return
        self.gravity = new_gravity
        self.gravity_shift_cooldown = 500
        self.gravity_shifting = True
        self.shift_animation_progress = 0
        self.shake_time = 18
        if self.current_piece:
            self.lock_piece()
        self.apply_gravity_to_board()
        self.clear_lines()
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
        kicks = [(0, 0), (-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0)]
        for kx, ky in kicks:
            if self.is_valid_position(self.current_piece, kx, ky):
                self.current_piece.x += kx
                self.current_piece.y += ky
                return
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

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key in (pygame.K_F11, pygame.K_f):
                    self.toggle_fullscreen()
                    continue
                if self.game_over:
                    if event.key == pygame.K_r:
                        self.reset_game()
                    continue
                if event.key == pygame.K_p:
                    self.paused = not self.paused
                    continue
                if self.paused:
                    continue
                if event.key == pygame.K_1:
                    self.shift_gravity(Gravity.DOWN)
                elif event.key == pygame.K_2:
                    self.shift_gravity(Gravity.UP)
                elif event.key == pygame.K_3:
                    self.shift_gravity(Gravity.LEFT)
                elif event.key == pygame.K_4:
                    self.shift_gravity(Gravity.RIGHT)
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

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: int):
        self.time_ms += dt
        if self.game_over or self.paused:
            return
        if self.gravity_shift_cooldown > 0:
            self.gravity_shift_cooldown -= dt
        if self.gravity_shifting:
            self.shift_animation_progress += dt / 200
            if self.shift_animation_progress >= 1:
                self.gravity_shifting = False
        if self.shake_time > 0:
            strength = max(2, self.shake_time // 2)
            self.shake_offset = [random.randint(-strength, strength),
                                  random.randint(-strength, strength)]
            self.shake_time -= 1
        else:
            self.shake_offset = [0, 0]
        self.particles = [p for p in self.particles if p.update()]
        self.fall_time += dt
        if self.fall_time >= self.fall_speed:
            self.fall_time = 0
            if not self.move_piece(0, 1):
                self.lock_piece()

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def _bx(self, col: int) -> int:
        return self.board_offset_x + col * CELL_SIZE + self.shake_offset[0]

    def _by(self, row: int) -> int:
        return self.board_offset_y + row * CELL_SIZE + self.shake_offset[1]

    def draw_board_frame(self):
        ox = self.board_offset_x + self.shake_offset[0]
        oy = self.board_offset_y + self.shake_offset[1]
        bw = BOARD_WIDTH  * CELL_SIZE
        bh = BOARD_HEIGHT * CELL_SIZE
        dx = DEPTH_OFFSET_X
        dy = DEPTH_OFFSET_Y

        # Top face
        top_pts = [
            (ox,        oy),
            (ox + bw,   oy),
            (ox + bw + dx, oy + dy),
            (ox + dx,      oy + dy),
        ]
        pygame.draw.polygon(self.screen, (40, 40, 80), top_pts)
        pygame.draw.polygon(self.screen, (100, 100, 180), top_pts, 1)

        # Right depth face
        right_pts = [
            (ox + bw,          oy),
            (ox + bw,          oy + bh),
            (ox + bw + dx,     oy + bh + dy),
            (ox + bw + dx,     oy + dy),
        ]
        pygame.draw.polygon(self.screen, (25, 25, 50), right_pts)
        pygame.draw.polygon(self.screen, (20, 20, 40), right_pts, 1)

        # Front face border
        pygame.draw.rect(self.screen, (60, 60, 110),
                         (ox + dx, oy + dy, bw, bh), 2)

    def draw_board_grid(self):
        ox = self.board_offset_x + self.shake_offset[0]
        oy = self.board_offset_y + self.shake_offset[1]
        dx = DEPTH_OFFSET_X
        dy = DEPTH_OFFSET_Y
        bw = BOARD_WIDTH  * CELL_SIZE
        bh = BOARD_HEIGHT * CELL_SIZE

        inner_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        inner_surf.fill((18, 18, 40, 230))
        self.screen.blit(inner_surf, (ox + dx, oy + dy))

        gc = COLORS['grid']
        for x in range(BOARD_WIDTH + 1):
            pygame.draw.line(self.screen, gc,
                             (ox + dx + x * CELL_SIZE, oy + dy),
                             (ox + dx + x * CELL_SIZE, oy + dy + bh))
        for y in range(BOARD_HEIGHT + 1):
            pygame.draw.line(self.screen, gc,
                             (ox + dx,      oy + dy + y * CELL_SIZE),
                             (ox + dx + bw, oy + dy + y * CELL_SIZE))

    def draw_board(self):
        self.draw_board_frame()
        self.draw_board_grid()

        # Placed blocks
        for y in range(BOARD_HEIGHT):
            for x in range(BOARD_WIDTH):
                if self.board[y][x]:
                    draw_block_3d(self.screen,
                                  self._bx(x), self._by(y),
                                  self.board[y][x])

        # Ghost piece
        if self.current_piece and not self.gravity_shifting:
            ghost_y = self.get_ghost_position()
            for bx, by in self.current_piece.blocks:
                gx = self.current_piece.x + bx
                gy = self.current_piece.y + by + ghost_y
                if 0 <= gy < BOARD_HEIGHT and 0 <= gx < BOARD_WIDTH:
                    draw_block_3d(self.screen,
                                  self._bx(gx), self._by(gy),
                                  self.current_piece.color, alpha=0.22)

        # Active piece
        if self.current_piece and not self.gravity_shifting:
            for bx, by in self.current_piece.blocks:
                gx = self.current_piece.x + bx
                gy = self.current_piece.y + by
                if 0 <= gy < BOARD_HEIGHT and 0 <= gx < BOARD_WIDTH:
                    draw_block_3d(self.screen,
                                  self._bx(gx), self._by(gy),
                                  self.current_piece.color, glow=True)

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    def draw_sidebar(self):
        sx = self.board_offset_x + BOARD_WIDTH * CELL_SIZE + DEPTH_OFFSET_X + 14
        sy = self.board_offset_y + DEPTH_OFFSET_Y

        panel_w = SIDEBAR_WIDTH - 10
        panel_h = BOARD_HEIGHT * CELL_SIZE
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((20, 20, 45, 200))
        pygame.draw.rect(panel_surf, (60, 60, 110), (0, 0, panel_w, panel_h), 1)
        self.screen.blit(panel_surf, (sx, sy))

        def text(msg, font, color, x, y):
            self.screen.blit(font.render(msg, True, color), (sx + x, sy + y))

        text("GRAVITY TETRIS 3D", self.title_font, COLORS['accent'], 6, 8)
        pygame.draw.line(self.screen, (60, 60, 110),
                         (sx + 4, sy + 30), (sx + panel_w - 4, sy + 30), 1)

        text("SCORE",      self.small_font, COLORS['text_dim'], 6, 40)
        text(f"{self.score:,}", self.font, COLORS['text'], 6, 58)
        text("LEVEL",      self.small_font, COLORS['text_dim'], 6, 95)
        text(str(self.level), self.font, COLORS['text'], 6, 113)
        text("LINES",      self.small_font, COLORS['text_dim'], 6, 150)
        text(str(self.lines_cleared), self.font, COLORS['text'], 6, 168)

        pygame.draw.line(self.screen, (60, 60, 110),
                         (sx + 4, sy + 205), (sx + panel_w - 4, sy + 205), 1)
        text("GRAVITY", self.small_font, COLORS['text_dim'], 6, 213)
        gravity_labels = {
            Gravity.DOWN:  "DOWN  [1]",
            Gravity.UP:    "UP    [2]",
            Gravity.LEFT:  "LEFT  [3]",
            Gravity.RIGHT: "RIGHT [4]",
        }
        text(gravity_labels[self.gravity], self.small_font, (100, 200, 255), 6, 233)

        # Arrow icon
        acx, acy = sx + 30, sy + 275
        pygame.draw.circle(self.screen, (40, 40, 70), (acx, acy), 22)
        pygame.draw.circle(self.screen, (60, 60, 100), (acx, acy), 22, 1)
        gdx, gdy = self.gravity.value
        pygame.draw.line(self.screen, (100, 200, 255),
                         (acx, acy), (acx + gdx * 16, acy + gdy * 16), 3)
        pygame.draw.circle(self.screen, (100, 200, 255),
                           (acx + gdx * 16, acy + gdy * 16), 3)

        if self.gravity_shift_cooldown > 0:
            text("Shifting...", self.small_font, (255, 200, 80), 58, 266)

        # Next piece preview
        pygame.draw.line(self.screen, (60, 60, 110),
                         (sx + 4, sy + 305), (sx + panel_w - 4, sy + 305), 1)
        text("NEXT", self.small_font, COLORS['text_dim'], 6, 313)
        if self.next_piece:
            for bx, by in TETROMINOES[self.next_piece.shape_type]:
                draw_block_3d(self.screen,
                              sx + 10 + bx * 22 - DEPTH_OFFSET_X,
                              sy + 335 + by * 22 - DEPTH_OFFSET_Y,
                              self.next_piece.color, cell=20)

        # Controls
        pygame.draw.line(self.screen, (60, 60, 110),
                         (sx + 4, sy + 400), (sx + panel_w - 4, sy + 400), 1)
        controls = [
            "CONTROLS",
            "Arrows  Move/Rotate",
            "Space   Hard Drop",
            "1-4     Gravity",
            "F/F11   Fullscreen",
            "P       Pause",
        ]
        for i, line in enumerate(controls):
            col = COLORS['accent'] if i == 0 else COLORS['text_dim']
            text(line, self.small_font, col, 6, 408 + i * 22)

    # ------------------------------------------------------------------
    # Overlays
    # ------------------------------------------------------------------
    def draw_overlay(self):
        if self.paused:
            ov = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            self.screen.blit(ov, (0, 0))
            msg = self.large_font.render("PAUSED", True, COLORS['text'])
            self.screen.blit(msg, msg.get_rect(center=(self.win_w // 2, self.win_h // 2)))
            sub = self.small_font.render("Press P to continue", True, COLORS['text_dim'])
            self.screen.blit(sub, sub.get_rect(center=(self.win_w // 2, self.win_h // 2 + 44)))

        if self.game_over:
            ov = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 185))
            self.screen.blit(ov, (0, 0))
            cx, cy = self.win_w // 2, self.win_h // 2
            go = self.large_font.render("GAME OVER", True, (255, 80, 80))
            self.screen.blit(go, go.get_rect(center=(cx, cy - 40)))
            sc = self.font.render(f"Score: {self.score:,}", True, COLORS['text'])
            self.screen.blit(sc, sc.get_rect(center=(cx, cy + 10)))
            lvl = self.small_font.render(
                f"Level {self.level}  •  {self.lines_cleared} lines",
                True, COLORS['text_dim'])
            self.screen.blit(lvl, lvl.get_rect(center=(cx, cy + 45)))
            rst = self.small_font.render("Press R to restart", True, (180, 180, 200))
            self.screen.blit(rst, rst.get_rect(center=(cx, cy + 80)))

        # Brief fullscreen hint at startup
        if self.time_ms < 4000:
            alpha = max(0, 255 - int(self.time_ms / 2000 * 255))
            hint_surf = self.small_font.render(
                "F / F11  →  Toggle Fullscreen", True, (180, 180, 220))
            hint_surf.set_alpha(alpha)
            self.screen.blit(hint_surf, (12, self.win_h - 26))

    # ------------------------------------------------------------------
    # Main draw
    # ------------------------------------------------------------------
    def draw(self):
        self._draw_background()
        self.draw_board()
        self.draw_sidebar()
        for p in self.particles:
            p.draw(self.screen)
        self.draw_overlay()
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
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
