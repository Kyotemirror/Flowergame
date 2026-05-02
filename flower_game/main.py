import json
import os
import random
import pygame


# ----------------------------
# Config loading
# ----------------------------
DEFAULT_CONFIG = {
    "width": 1000,
    "height": 700,
    "cell_size": 10,
    "fps": 30,
    "max_age": 18,
    "fade_rate": 1,
    "birth_2_chance": 0.18,
    "spread_chance": 0.03,
    "wither_old_at": 12,
    "fullscreen": False,
    "touch": {"enabled": True, "brush_radius": 2, "erase_strength": 4},
    "grid_lines": True,
}

def load_config(path="config.json"):
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            # shallow merge + nested merge for touch
            cfg.update(user_cfg)
            if "touch" in user_cfg and isinstance(user_cfg["touch"], dict):
                merged_touch = DEFAULT_CONFIG["touch"].copy()
                merged_touch.update(user_cfg["touch"])
                cfg["touch"] = merged_touch
        except Exception:
            # If config is malformed, fall back to defaults silently
            pass
    return cfg


cfg = load_config()

# Settings
WIDTH, HEIGHT = int(cfg["width"]), int(cfg["height"])
CELL_SIZE = int(cfg["cell_size"])
COLS = WIDTH // CELL_SIZE
ROWS = HEIGHT // CELL_SIZE
FPS = int(cfg["fps"])

MAX_AGE = int(cfg["max_age"])
FADE_RATE = int(cfg["fade_rate"])

BIRTH_3 = True
BIRTH_2_CHANCE = float(cfg["birth_2_chance"])
SPREAD_CHANCE = float(cfg["spread_chance"])
WITHER_OLD_AT = int(cfg["wither_old_at"])

TOUCH_ENABLED = bool(cfg.get("touch", {}).get("enabled", True))
BRUSH_RADIUS = int(cfg.get("touch", {}).get("brush_radius", 2))
ERASE_STRENGTH = int(cfg.get("touch", {}).get("erase_strength", 4))

FULLSCREEN = bool(cfg.get("fullscreen", False))
DRAW_GRID_LINES = bool(cfg.get("grid_lines", True))

# Colors
BG = (10, 10, 20)
GRID = (30, 30, 50)
TEXT = (220, 220, 255)

# "Flower" palette endpoints (young -> old)
YOUNG = (120, 255, 160)
OLD = (200, 120, 255)

pygame.init()

flags = pygame.FULLSCREEN if FULLSCREEN else 0
screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
pygame.display.set_caption("The Flower Game — Bloom Mode")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 18)

# Grid holds age (0..MAX_AGE)
grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
running = False
generation = 0


# ----------------------------
# Helpers
# ----------------------------
def lerp(a, b, t):
    return int(a + (b - a) * t)

def blend(c1, c2, t):
    return (
        lerp(c1[0], c2[0], t),
        lerp(c1[1], c2[1], t),
        lerp(c1[2], c2[2], t),
    )

def paint_circle(gx, gy, value=1, soften_erase=False):
    """Paint a circular brush. If soften_erase=True, reduce age instead of hard 0."""
    r = BRUSH_RADIUS
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                x = gx + dx
                y = gy + dy
                if 0 <= x < COLS and 0 <= y < ROWS:
                    if value == 0 and soften_erase:
                        grid[y][x] = max(0, grid[y][x] - ERASE_STRENGTH)
                    else:
                        grid[y][x] = value

def count_neighbors_alive(g, x, y):
    """Count neighbors that are alive (age > 0). Toroidal wrap."""
    count = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx = (x + dx) % COLS
            ny = (y + dy) % ROWS
            if g[ny][nx] > 0:
                count += 1
    return count

def neighbor_has_life(g, x, y):
    """Is there any life in a 2-radius neighborhood? Helps branching blooms."""
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            if dx == 0 and dy == 0:
                continue
            nx = (x + dx) % COLS
            ny = (y + dy) % ROWS
            if g[ny][nx] > 0:
                return True
    return False

def update_grid(g):
    new_g = [[0 for _ in range(COLS)] for _ in range(ROWS)]

    for y in range(ROWS):
        for x in range(COLS):
            age = g[y][x]
            n = count_neighbors_alive(g, x, y)
            alive = age > 0

            if alive:
                survive = (n == 2 or n == 3)

                # Wither: old cells have a small extra chance to die
                if survive and age >= WITHER_OLD_AT and random.random() < 0.06:
                    survive = False

                if survive:
                    new_g[y][x] = min(MAX_AGE, age + 1)
                else:
                    new_g[y][x] = max(0, age - FADE_RATE)
            else:
                born = False

                if BIRTH_3 and n == 3:
                    born = True

                if (not born) and n == 2 and neighbor_has_life(g, x, y):
                    if random.random() < BIRTH_2_CHANCE:
                        born = True

                if (not born) and random.random() < SPREAD_CHANCE and neighbor_has_life(g, x, y):
                    born = True

                new_g[y][x] = 1 if born else 0

    return new_g

def cell_color(age):
    """Map age to a flower-like gradient + fade toward BG for trails."""
    if age <= 0:
        return None

    t = (age - 1) / (MAX_AGE - 1) if MAX_AGE > 1 else 0
    base = blend(YOUNG, OLD, t)

    fade_t = 0.55 * (1 - t)
    return blend(base, BG, fade_t)

def draw_grid(g):
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            age = g[y][x]
            c = cell_color(age)
            if c is None:
                pygame.draw.rect(screen, BG, rect)
            else:
                pygame.draw.rect(screen, c, rect)

            if DRAW_GRID_LINES:
                pygame.draw.rect(screen, GRID, rect, 1)

def randomize():
    g = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    for _ in range((COLS * ROWS) // 80):
        x = random.randrange(COLS)
        y = random.randrange(ROWS)
        g[y][x] = random.randint(1, 4)
    return g

def clear():
    return [[0 for _ in range(COLS)] for _ in range(ROWS)]


# ----------------------------
# Main loop
# ----------------------------
while True:
    screen.fill(BG)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                running = not running
            elif event.key == pygame.K_c:
                grid = clear()
                generation = 0
            elif event.key == pygame.K_r:
                grid = randomize()
                generation = 0
            elif event.key == pygame.K_UP:
                FPS = min(60, FPS + 1)
            elif event.key == pygame.K_DOWN:
                FPS = max(1, FPS - 1)
            elif event.key == pygame.K_ESCAPE and FULLSCREEN:
                # Convenience: allow exit fullscreen apps during testing
                pygame.quit()
                raise SystemExit

        # Touchscreen-friendly input (native touch events)
        if TOUCH_ENABLED and event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION):
            gx = int(event.x * COLS)
            gy = int(event.y * ROWS)
            if 0 <= gx < COLS and 0 <= gy < ROWS:
                paint_circle(gx, gy, value=1)

    # Mouse fallback (works on desktop and touch that emulates mouse)
    mx, my = pygame.mouse.get_pos()
    gx = mx // CELL_SIZE
    gy = my // CELL_SIZE
    if 0 <= gx < COLS and 0 <= gy < ROWS:
        left, _, right = pygame.mouse.get_pressed()
        if left:
            paint_circle(gx, gy, value=1)
        elif right:
            paint_circle(gx, gy, value=0, soften_erase=True)

    if running:
        grid = update_grid(grid)
        generation += 1
    else:
        # gentle fade while paused (Zen settling)
        for y in range(ROWS):
            for x in range(COLS):
                if grid[y][x] > 0 and random.random() < 0.02:
                    grid[y][x] = max(0, grid[y][x] - 1)

    draw_grid(grid)

    status = "RUNNING" if running else "PAUSED"
    hud = (
        f"[SPACE] Start/Pause   [R] Seed Random   [C] Clear   [↑/↓] Speed({FPS})   "
        f"Gen: {generation}   Status: {status}"
    )
    screen.blit(font.render(hud, True, TEXT), (10, HEIGHT - 26))

    pygame.display.flip()
    clock.tick(FPS)
