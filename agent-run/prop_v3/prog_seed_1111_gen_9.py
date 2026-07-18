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

def get_conflict_pairs(circles, threshold=0.01):
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
# STEP 1: Four-strategy initial placement with better spacing
# ==============================================================================

# Strategy A: Improved hexagonal packing with optimization
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

# Strategy B: Golden spiral with adaptive radii
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

# Strategy C: Perturbed grid with spacing awareness
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

# Strategy D: Optimized corner/edge placement for extreme positions
circles_corner = []
corners = [(0.08, 0.08), (0.92, 0.08), (0.08, 0.92), (0.92, 0.92)]
for corner in corners:
    circles_corner.append([corner[0], corner[1], 0.014])

# Fill remaining with golden spiral
center_x, center_y = 0.5, 0.5
idx = 4
while len(circles_corner) < 26:
    i = idx - 4
    angle = 2 * math.pi * i / golden_ratio
    r_from_center = 0.32 * math.sqrt(i / 22.0)
    x = center_x + r_from_center * math.cos(angle)
    y = center_y + r_from_center * math.sin(angle)
    x = max(0.02, min(0.98, x))
    y = max(0.02, min(0.98, y))
    circles_corner.append([x, y, 0.014])
    idx += 1

circles_corner = circles_corner[:26]

best_overall = None
best_score = -1

for strategy_circles in [circles_hex, circles_spiral, circles_grid, circles_corner]:
    circles = [c[:] for c in strategy_circles]

    # ==============================================================================
    # STEP 2: Aggressive radius growth with conflict awareness
    # ==============================================================================
    for iteration in range(6000):
        old_radii = [c[2] for c in circles]

        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            increment = min(0.003, max_r - circles[i][2])
            circles[i][2] = max(0, circles[i][2] + increment)

        new_radii = [c[2] for c in circles]
        max_delta = max(abs(new_radii[i] - old_radii[i]) for i in range(26)) if new_radii else 0

        if max_delta < 1e-12:
            break

    # ==============================================================================
    # STEP 3: Conflict-aware position optimization
    # ==============================================================================
    for scale_idx, step_size in enumerate([0.024, 0.014, 0.008, 0.004, 0.002]):
        for shift_iter in range(150):
            shifted = False

            # Get conflicts to prioritize moving conflicted circles
            conflicts = get_conflict_pairs(circles, threshold=0.015)
            priority_indices = set()
            for i, j, gap in conflicts:
                priority_indices.add(i)
                priority_indices.add(j)

            # Process priority circles first, then others
            process_order = list(priority_indices) + [i for i in range(26) if i not in priority_indices]

            for i in process_order:
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
    # STEP 4: Targeted conflict resolution with direction-aware moves
    # ==============================================================================
    for conflict_pass in range(12):
        conflicts = get_conflict_pairs(circles, threshold=0.006)
        if not conflicts:
            break

        conflicts.sort(key=lambda x: x[2])

        handled_pairs = set()
        for i, j, gap in conflicts[:15]:  # Handle top 15 conflicts
            if (i, j) in handled_pairs:
                continue
            handled_pairs.add((i, j))

            dx_ij = circles[i][0] - circles[j][0]
            dy_ij = circles[i][1] - circles[j][1]
            dist_ij = math.sqrt(dx_ij*dx_ij + dy_ij*dy_ij) + 1e-10

            # Move both circles apart from conflict center
            for circle_idx, direction in [(i, 1), (j, -1)]:
                x, y, r = circles[circle_idx]
                best_r = r
                best_x, best_y = x, y

                nudge_x = direction * dx_ij / dist_ij * 0.008
                nudge_y = direction * dy_ij / dist_ij * 0.008

                for scale in [1.0, 0.7, 0.4, 0.0]:
                    for offx, offy in [(-0.004, -0.004), (-0.004, 0), (-0.004, 0.004),
                                       (0, -0.004), (0, 0), (0, 0.004),
                                       (0.004, -0.004), (0.004, 0), (0.004, 0.004)]:
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
    # STEP 5: Aggressive fine-scale refinement
    # ==============================================================================
    for step_size in [0.0018, 0.0010, 0.0005, 0.00025]:
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
    # STEP 6: Aggressive radius maximization passes
    # ==============================================================================
    for _ in range(2000):
        changed = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed = True
        if not changed:
            break

    # ==============================================================================
    # STEP 7: Ultra-fine refinement at extreme precision
    # ==============================================================================
    for shift_iter in range(80):
        shifted = False
        for i in range(26):
            x, y, r = circles[i]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.00025, 0, 0.00025]:
                for dy in [-0.00025, 0, 0.00025]:
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
    # STEP 8: Final cleanup and validation
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
