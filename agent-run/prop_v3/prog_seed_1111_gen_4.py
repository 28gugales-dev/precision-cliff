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
            if d < sum_r + 0.01:
                pairs.append((i, j, d - sum_r))
    return pairs

# ==============================================================================
# STEP 1: Multi-strategy initial placement
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

        circles_hex.append([x, y, 0.02])
        col += 1

    row += 1

circles_hex = circles_hex[:26]

# Strategy B: Adaptive grid with better boundary handling
circles_grid = []
grid_size = int(math.ceil(math.sqrt(26)))
margin = 0.05

for i in range(grid_size):
    for j in range(grid_size):
        if len(circles_grid) >= 26:
            break

        x = margin + (1 - 2*margin) * i / max(1, grid_size - 1)
        y = margin + (1 - 2*margin) * j / max(1, grid_size - 1)

        # Add slight random perturbation
        x += random.uniform(-0.007, 0.007)
        y += random.uniform(-0.007, 0.007)

        x = max(0, min(1, x))
        y = max(0, min(1, y))

        circles_grid.append([x, y, 0.015])

circles_grid = circles_grid[:26]

best_overall = None
best_score = -1

for strategy_circles in [circles_hex, circles_grid]:
    circles = [c[:] for c in strategy_circles]

    # ==============================================================================
    # STEP 2: Aggressive phase - grow radii rapidly
    # ==============================================================================
    for iteration in range(3000):
        old_radii = [c[2] for c in circles]

        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            increment = min(0.0015, max_r - circles[i][2])
            circles[i][2] = max(0, circles[i][2] + increment)

        new_radii = [c[2] for c in circles]
        max_delta = max(abs(new_radii[i] - old_radii[i]) for i in range(26)) if new_radii else 0

        if max_delta < 5e-12:
            break

    # ==============================================================================
    # STEP 3: Coarse-grained position adjustment (large steps)
    # ==============================================================================
    for shift_iter in range(100):
        shifted = False
        for i in range(26):
            x, y, r = circles[i]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.012, -0.006, 0, 0.006, 0.012]:
                for dy in [-0.012, -0.006, 0, 0.006, 0.012]:
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
    # STEP 4: Radius maximization after coarse adjustment
    # ==============================================================================
    for _ in range(500):
        changed = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed = True
        if not changed:
            break

    # ==============================================================================
    # STEP 5: Medium-scale position adjustment
    # ==============================================================================
    for step_size in [0.008, 0.004]:
        for shift_iter in range(120):
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
    # STEP 6: Fine-scale position adjustment
    # ==============================================================================
    for step_size in [0.002, 0.001]:
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
    # STEP 7: Targeted refinement for conflict pairs
    # ==============================================================================
    for conflict_pass in range(3):
        conflicts = get_conflict_pairs(circles)
        if not conflicts:
            break

        # Sort by gap (most negative first - most overlapping)
        conflicts.sort(key=lambda x: x[2])

        for i, j, gap in conflicts[:8]:  # Focus on worst conflicts
            # Try to improve circle i
            x, y, r = circles[i]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.003, -0.0015, 0, 0.0015, 0.003]:
                for dy in [-0.003, -0.0015, 0, 0.0015, 0.003]:
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

            circles[i] = [best_x, best_y, best_r]

            # Try to improve circle j similarly
            x, y, r = circles[j]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.003, -0.0015, 0, 0.0015, 0.003]:
                for dy in [-0.003, -0.0015, 0, 0.0015, 0.003]:
                    if dx == 0 and dy == 0:
                        continue

                    nx = x + dx
                    ny = y + dy

                    if 0 <= nx <= 1 and 0 <= ny <= 1:
                        nr = get_max_radius(nx, ny, circles, j)
                        if nr > best_r + 1e-12:
                            best_r = nr
                            best_x = nx
                            best_y = ny

            circles[j] = [best_x, best_y, best_r]

    # ==============================================================================
    # STEP 8: Ultra-fine position search
    # ==============================================================================
    for shift_iter in range(80):
        shifted = False
        for i in range(26):
            x, y, r = circles[i]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.0015, 0, 0.0015]:
                for dy in [-0.0015, 0, 0.0015]:
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
    # STEP 9: Final radius maximization pass
    # ==============================================================================
    for _ in range(500):
        changed = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed = True
        if not changed:
            break

    # ==============================================================================
    # STEP 10: Cleanup and validation
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
