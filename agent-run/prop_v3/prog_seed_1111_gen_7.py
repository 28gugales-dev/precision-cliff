import math
import random

random.seed(1111)

def dist(c1, c2):
    """Euclidean distance between circle centers."""
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

def get_max_radius(x, y, circles, idx):
    """Get maximum radius for a circle at (x,y) given other circles."""
    r_max = min(x, 1 - x, y, 1 - y)
    for j in range(len(circles)):
        if j != idx:
            d = dist([x, y, 0], circles[j])
            r_max = min(r_max, max(0, d - circles[j][2]))
    return max(0, r_max)

def get_conflict_pairs(circles, threshold=0.012):
    """Find pairs of circles that are overlapping or nearly so."""
    pairs = []
    for i in range(len(circles)):
        for j in range(i + 1, len(circles)):
            d = dist(circles[i], circles[j])
            sum_r = circles[i][2] + circles[j][2]
            gap = d - sum_r
            if gap < threshold:
                pairs.append((i, j, gap))
    return pairs

# ==============================================================================
# STEP 1: Multi-strategy initial placement (improved)
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

# Strategy B: Golden spiral placement for better spread
circles_spiral = []
center_x, center_y = 0.5, 0.5
golden_ratio = (1 + math.sqrt(5)) / 2
for i in range(26):
    angle = 2 * math.pi * i / golden_ratio
    r_from_center = 0.38 * math.sqrt(i / 26.0)
    x = center_x + r_from_center * math.cos(angle)
    y = center_y + r_from_center * math.sin(angle)
    x = max(0.02, min(0.98, x))
    y = max(0.02, min(0.98, y))
    circles_spiral.append([x, y, 0.014])

# Strategy C: Adaptive perturbed grid
circles_grid = []
grid_size = int(math.ceil(math.sqrt(26)))
margin = 0.06
for i in range(grid_size):
    for j in range(grid_size):
        if len(circles_grid) >= 26:
            break
        x = margin + (1 - 2*margin) * i / max(1, grid_size - 1)
        y = margin + (1 - 2*margin) * j / max(1, grid_size - 1)
        x += random.uniform(-0.01, 0.01)
        y += random.uniform(-0.01, 0.01)
        x = max(0, min(1, x))
        y = max(0, min(1, y))
        circles_grid.append([x, y, 0.013])

circles_grid = circles_grid[:26]

best_overall = None
best_score = -1

for strategy_circles in [circles_hex, circles_spiral, circles_grid]:
    circles = [c[:] for c in strategy_circles]

    # ==============================================================================
    # STEP 2: Ultra-aggressive radius growth phase
    # ==============================================================================
    for iteration in range(5000):
        old_radii = [c[2] for c in circles]

        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            increment = min(0.0028, max_r - circles[i][2])
            circles[i][2] = max(0, circles[i][2] + increment)

        new_radii = [c[2] for c in circles]
        max_delta = max(abs(new_radii[i] - old_radii[i]) for i in range(26)) if new_radii else 0

        if max_delta < 2e-12:
            break

    # ==============================================================================
    # STEP 3: Aggressive multi-scale position optimization
    # ==============================================================================
    for step_size in [0.018, 0.01, 0.005, 0.0025]:
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
    # STEP 4: Radius maximization pass
    # ==============================================================================
    for _ in range(1200):
        changed = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed = True
        if not changed:
            break

    # ==============================================================================
    # STEP 5: Targeted conflict resolution (all conflicts, not just top 12)
    # ==============================================================================
    for conflict_pass in range(8):
        conflicts = get_conflict_pairs(circles, threshold=0.008)
        if not conflicts:
            break

        conflicts.sort(key=lambda x: x[2])

        # Handle all conflicts with smart neighbor-aware moves
        handled_pairs = set()
        for i, j, gap in conflicts:
            if (i, j) in handled_pairs:
                continue
            handled_pairs.add((i, j))

            # Direction from j to i
            dx_ij = circles[i][0] - circles[j][0]
            dy_ij = circles[i][1] - circles[j][1]
            dist_ij = math.sqrt(dx_ij*dx_ij + dy_ij*dy_ij) + 1e-10

            # Try nudging both circles apart
            for circle_idx, direction in [(i, 1), (j, -1)]:
                x, y, r = circles[circle_idx]
                best_r = r
                best_x, best_y = x, y

                # Primary direction: away from conflict
                nudge_x = direction * dx_ij / dist_ij * 0.006
                nudge_y = direction * dy_ij / dist_ij * 0.006

                for scale in [1.0, 0.5, 0.0]:
                    for offx, offy in [(-0.003, -0.003), (-0.003, 0), (-0.003, 0.003),
                                       (0, -0.003), (0, 0), (0, 0.003),
                                       (0.003, -0.003), (0.003, 0), (0.003, 0.003)]:
                        nx = x + scale * nudge_x + offx
                        ny = y + scale * nudge_y + offy
                        if 0 <= nx <= 1 and 0 <= ny <= 1:
                            nr = get_max_radius(nx, ny, circles, circle_idx)
                            if nr > best_r + 1e-12:
                                best_r = nr
                                best_x = nx
                                best_y = ny

                circles[circle_idx] = [best_x, best_y, best_r]

    # ==============================================================================
    # STEP 6: Fine-scale refinement with adaptive step
    # ==============================================================================
    for step_size in [0.002, 0.0012, 0.0006]:
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
    # STEP 7: Final aggressive radius maximization
    # ==============================================================================
    for _ in range(1500):
        changed = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed = True
        if not changed:
            break

    # ==============================================================================
    # STEP 8: Ultra-fine refinement at sub-pixel scale
    # ==============================================================================
    for shift_iter in range(60):
        shifted = False
        for i in range(26):
            x, y, r = circles[i]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.0003, 0, 0.0003]:
                for dy in [-0.0003, 0, 0.0003]:
                    if dx == 0 and dy == 0:
                        continue
                    nx = x + dx
                    ny = y + dy
                    if 0 <= nx <= 1 and 0 <= ny <= 1:
                        nr = get_max_radius(nx, ny, circles, i)
                        if nr > best_r + 1e-13:
                            best_r = nr
                            best_x = nx
                            best_y = ny
                            shifted = True

            circles[i] = [best_x, best_y, best_r]

        if not shifted:
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

    current_score = sum(c[2] for c in circles)
    if current_score > best_score:
        best_score = current_score
        best_overall = circles

print(best_overall)
