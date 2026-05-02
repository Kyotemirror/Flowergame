import pygame
import random

pygame.init()

# Settings
WIDTH, HEIGHT = 1000, 700
CELL_SIZE = 10
COLS = WIDTH // CELL_SIZE
ROWS = HEIGHT // CELL_SIZE
FPS = 30

# Colors
BG = (10, 10, 20)
GRID = (30, 30, 50)
TEXT = (220, 220, 255)

# "Flower" palette endpoints (young -> old)
YOUNG = (120, 255, 160)   # bright green
OLD   = (200, 120, 255)   # petal purple

# Aging/trails
MAX_AGE = 18          # how long trails last (higher = longer trails)
FADE_RATE = 1         # age decrement per frame for dead cells

# Growth tuning (try small tweaks here)
BIRTH_3 = True
BIRTH_2_CHANCE = 0.18     # chance to birth with exactly 2 neighbors (flower branching)
SPREAD_CHANCE = 0.03      # rare "spore" spread for organic feel
WITHER_OLD_AT = 12        # old cells start to wither easier

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("The Flower Game — Bloom Mode")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 18)

# Grid holds age (0..MAX_AGE)
grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
running = False
generation = 0


def lerp(a, b, t):
    return int(a + (b - a) * t)

def blend(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))

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
                # Survival: classic 2-3 neighbors, but older cells wither easier
                survive = (n == 2 or n == 3)

                # Wither: if old, slightly higher chance to die even if "stable"
                if survive and age >= WITHER_OLD_AT and random.random() < 0.06:
                    survive = False

                if survive:
                    # "Life" continues: increase age up to MAX_AGE for richer petals
                    new_g[y][x] = min(MAX_AGE, age + 1)
                else:
                    # Fade trail instead of instant death
                    new_g[y][x] = max(0, age - FADE_RATE)

            else:
                # Birth rules for bloom/branchiness
                born = False

                # Standard Life birth on 3
                if BIRTH_3 and n == 3:
                    born = True

                # Flower branching: occasionally birth on 2 if there's nearby life
                if (not born) and n == 2 and neighbor_has_life(g, x, y):
                    if random.random() < BIRTH_2_CHANCE:
                        born = True

                # Spores: rare spread near living cells (organic growth)
                if (not born) and random.random() < SPREAD_CHANCE and neighbor_has_life(g, x, y):
                    born = True

                new_g[y][x] = 1 if born else 0

    return new_g

def cell_color(age):
    """Map age to a flower-like gradient + fade toward BG for trails."""
    if age <= 0:
        return None

    # Normalize age 1..MAX_AGE => 0..1
    t = (age - 1) / (MAX_AGE - 1) if MAX_AGE > 1 else 0

    # Young->Old petal gradient
    base = blend(YOUNG, OLD, t)

    # Fade effect: lower ages (trails) blend more toward BG
    # Here, "brightness" increases with age; trails are darker.
    fade_t = 0.55 * (1 - t)  # young trails = more BG blended
    return blend(base, BG, fade_t)

def draw_grid(g):
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)

            age = g[y][x]
            c = cell_color(age)
            if c is None:
                # dead space
                pygame.draw.rect(screen, blend(BG, (0,0,0), 0.0), rect)
            else:
                pygame.draw.rect(screen, c, rect)

            pygame.draw.rect(screen, GRID, rect, 1)

def randomize():
    # start with a few "seeds" not full noise (more flower-like)
    g = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    for _ in range((COLS * ROWS) // 80):
        x = random.randrange(COLS)
        y = random.randrange(ROWS)
        g[y][x] = random.randint(1, 4)
    return g

def clear():
    return [[0 for _ in range(COLS)] for _ in range(ROWS)]


while True:
    screen.fill(BG)

    # --- Events ---
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

    # --- Smooth painting (left = plant, right = erase) ---
    mx, my = pygame.mouse.get_pos()
    gx = mx // CELL_SIZE
    gy = my // CELL_SIZE
    if 0 <= gx < COLS and 0 <= gy < ROWS:
        left, _, right = pygame.mouse.get_pressed()
        if left:
            grid[gy][gx] = 1
        elif right:
            grid[gy][gx] = 0

    # --- Update ---
    if running:
        grid = update_grid(grid)
        generation += 1
    else:
        # Even paused, let trails gently fade (optional)
        # Comment this out if you want fully static pause.
        for y in range(ROWS):
            for x in range(COLS):
                if grid[y][x] > 0 and random.random() < 0.02:
                    grid[y][x] = max(0, grid[y][x] - 1)

    # --- Draw ---
    draw_grid(grid)

    status = "RUNNING" if running else "PAUSED"
    hud = (
        f"[SPACE] Start/Pause   [R] Seed Random   [C] Clear   [↑/↓] Speed({FPS})   "
        f"Gen: {generation}   Status: {status}"
    )
    screen.blit(font.render(hud, True, TEXT), (10, HEIGHT - 26))

    pygame.display.flip()
    clock.tick(FPS)