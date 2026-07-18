import math
import random

random.seed(1111)

def dist(c1, c2):
    """Euclidean distance between circle centers."""
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

def in_bounds(x, y, r):
    """Check if circle is strictly inside [0,1]x[0,1]."""
    return x - r >= -1e-10 and x + r <= 1 + 1e-10 and y - r >= -1e-10 and y + r <= 1 + 1e-10

def get_max_radius(x, y, circles, idx):
    """Get maximum radius for a circle at (x,y) given other circles."""
    r_max = min(x, 1 - x, y, 1 - y)

    for j in range(len(circles)):
        if j != idx:
            d = dist([x, y, 0], circles[j])
            r_max = min(r_max, max(0, d - circles[j][2]))

    return max(0, r_max)

def get_conflict_pairs(circles):
    """Find pairs of circles that are touching or nearly overlapping."""
    pairs = []
    for i in range(len(circles)):
        for j in range(i + 1, len(circles)):
            d = dist(circles[i], circles[j])
            sum_r = circles[i][2] + circles[j][2]
            if d < sum_r + 0.015:
                pairs.append((i, j, d - sum_r))
    return pairs

# ==============================================================================
# STEP 1: Multi-strategy initial placement with three approaches
# ==============================================================================

# Strategy A: Hexagonal packing (proven good)
circles_hex = []
n_cols = 6
hex_spacing_x = 1.0 / (n_cols - 1)
hex_spacing_y = hex_spacing_x * math.sqrt(3) / 2

row = 0
while len(circles_hex) < 26:
    y = row * hex_spacing_y
    if y > 1.0 + 1e-9:
        break

    x_offset = hex_spacing_x / 2 if row % 2 == 1 else 0

    col = 0
    while len(circles_hex) < 26:
        x = col * hex_spacing_x + x_offset
        if x > 1.0 + 1e-9:
            break

        x = min(x, 1.0)
        y = min(y, 1.0)

        circles_hex.append([x, y, 0.015])
        col += 1

    row += 1

circles_hex = circles_hex[:26]

# Strategy B: Adaptive grid with boundary handling
circles_grid = []
grid_size = int(math.ceil(math.sqrt(26)))
margin = 0.05

for i in range(grid_size):
    for j in range(grid_size):
        if len(circles_grid) >= 26:
            break

        x = margin + (1 - 2*margin) * i / max(1, grid_size - 1)
        y = margin + (1 - 2*margin) * j / max(1, grid_size - 1)

        x += random.uniform(-0.008, 0.008)
        y += random.uniform(-0.008, 0.008)

        x = max(0, min(1, x))
        y = max(0, min(1, y))

        circles_grid.append([x, y, 0.012])

circles_grid = circles_grid[:26]

# Strategy C: Greedy smart placement - place circles one by one optimally
circles_greedy = []
placed_positions = set()

# Start with a grid to get initial positions, then refine via greedy growth
candidate_positions = []
for i in range(6):
    for j in range(5):
        x = 0.1 + i * 0.15
        y = 0.1 + j * 0.16
        if x <= 1.0 and y <= 1.0:
            candidate_positions.append((x, y))

candidate_positions.sort(key=lambda p: (p[0] + p[1], random.random()))

for idx, (x, y) in enumerate(candidate_positions[:26]):
    if idx < 26:
        max_r = get_max_radius(x, y, circles_greedy, len(circles_greedy))
        max_r = max(0.01, min(max_r, 0.08))
        circles_greedy.append([x, y, max_r])

best_overall = None
best_score = -1

for strategy_circles in [circles_hex, circles_grid, circles_greedy]:
    circles = [c[:] for c in strategy_circles]

    # ==============================================================================
    # STEP 2: Very aggressive phase - grow radii as fast as possible
    # ==============================================================================
    for iteration in range(4000):
        old_radii = [c[2] for c in circles]

        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            increment = min(0.002, max_r - circles[i][2])
            circles[i][2] = max(0, circles[i][2] + increment)

        new_radii = [c[2] for c in circles]
        max_delta = max(abs(new_radii[i] - old_radii[i]) for i in range(26)) if new_radii else 0

        if max_delta < 3e-12:
            break

    # ==============================================================================
    # STEP 3: Aggressive coarse-grained position adjustment
    # ==============================================================================
    for shift_iter in range(150):
        shifted = False
        for i in range(26):
            x, y, r = circles[i]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.015, -0.0075, 0, 0.0075, 0.015]:
                for dy in [-0.015, -0.0075, 0, 0.0075, 0.015]:
                    if dx == 0 and dy == 0:
                        continue

                    nx = x + dx
                    ny = y + dy

                    if 0 <= nx <= 1 and 0 <= ny <= 1:
                        nr = get_max_radius(nx, ny, circles, i)
                        if nr > best_r + 1e-12:
                            best_r = nr
                            best_x = nx
                            best_y = ny
                            shifted = True

            circles[i] = [best_x, best_y, best_r]

        if not shifted:
            break

    # ==============================================================================
    # STEP 4: Radius maximization
    # ==============================================================================
    for _ in range(600):
        changed = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed = True
        if not changed:
            break

    # ==============================================================================
    # STEP 5: Multi-scale position adjustment
    # ==============================================================================
    for step_size in [0.01, 0.006, 0.003]:
        for shift_iter in range(150):
            shifted = False
            for i in range(26):
                x, y, r = circles[i]
                best_r = r
                best_x, best_y = x, y

                for dx in [-step_size, 0, step_size]:
                    for dy in [-step_size, 0, step_size]:
                        if dx == 0 and dy == 0:
                            continue

                        nx = x + dx
                        ny = y + dy

                        if 0 <= nx <= 1 and 0 <= ny <= 1:
                            nr = get_max_radius(nx, ny, circles, i)
                            if nr > best_r + 1e-12:
                                best_r = nr
                                best_x = nx
                                best_y = ny
                                shifted = True

                circles[i] = [best_x, best_y, best_r]

            if not shifted:
                break

    # ==============================================================================
    # STEP 6: Targeted aggressive conflict resolution
    # ==============================================================================
    for conflict_pass in range(5):
        conflicts = get_conflict_pairs(circles)
        if not conflicts:
            break

        conflicts.sort(key=lambda x: x[2])

        for i, j, gap in conflicts[:12]:
            # Aggressively try to resolve this conflict
            for circle_idx in [i, j]:
                x, y, r = circles[circle_idx]
                best_r = r
                best_x, best_y = x, y

                for dx in [-0.004, -0.002, 0, 0.002, 0.004]:
                    for dy in [-0.004, -0.002, 0, 0.002, 0.004]:
                        if dx == 0 and dy == 0:
                            continue

                        nx = x + dx
                        ny = y + dy

                        if 0 <= nx <= 1 and 0 <= ny <= 1:
                            nr = get_max_radius(nx, ny, circles, circle_idx)
                            if nr > best_r + 1e-12:
                                best_r = nr
                                best_x = nx
                                best_y = ny

                circles[circle_idx] = [best_x, best_y, best_r]

    # ==============================================================================
    # STEP 7: Fine-scale refinement
    # ==============================================================================
    for step_size in [0.0015, 0.0008]:
        for shift_iter in range(100):
            shifted = False
            for i in range(26):
                x, y, r = circles[i]
                best_r = r
                best_x, best_y = x, y

                for dx in [-step_size, 0, step_size]:
                    for dy in [-step_size, 0, step_size]:
                        if dx == 0 and dy == 0:
                            continue

                        nx = x + dx
                        ny = y + dy

                        if 0 <= nx <= 1 and 0 <= ny <= 1:
                            nr = get_max_radius(nx, ny, circles, i)
                            if nr > best_r + 1e-12:
                                best_r = nr
                                best_x = nx
                                best_y = ny
                                shifted = True

                circles[i] = [best_x, best_y, best_r]

            if not shifted:
                break

    # ==============================================================================
    # STEP 8: Final radius maximization pass
    # ==============================================================================
    for _ in range(800):
        changed = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed = True
        if not changed:
            break

    # ==============================================================================
    # STEP 9: Cleanup and validation
    # ==============================================================================
    for i in range(26):
        x, y, r = circles[i]

        r = min(r, x, 1 - x, y, 1 - y)
        circles[i][2] = max(0, r)

        circles[i][0] = max(0, min(1, x))
        circles[i][1] = max(0, min(1, y))

    # Verify and compute score
    current_score = sum(c[2] for c in circles)
    if current_score > best_score:
        best_score = current_score
        best_overall = circles

print(best_overall)
