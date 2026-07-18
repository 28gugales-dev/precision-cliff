import math
import random
import itertools

random.seed(1111)

def dist(c1, c2):
    """Euclidean distance between circle centers."""
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

def in_bounds(x, y, r):
    """Check if circle is strictly inside [0,1]x[0,1]."""
    return x - r >= -1e-10 and x + r <= 1 + 1e-10 and y - r >= -1e-10 and y + r <= 1 + 1e-10

def get_max_radius_binary(x, y, circles, idx):
    """Get maximum radius using binary search for faster convergence."""
    r_bound = min(x, 1 - x, y, 1 - y)

    if r_bound < 1e-12:
        return 0.0

    # Binary search for maximum radius that doesn't overlap
    r_min, r_max = 0.0, r_bound

    for _ in range(40):  # Binary search iterations
        r_mid = (r_min + r_max) / 2.0

        # Check if r_mid is valid
        valid = True
        for j in range(len(circles)):
            if j != idx:
                d = dist([x, y, 0], circles[j])
                if d < r_mid + circles[j][2] - 1e-12:
                    valid = False
                    break

        if valid:
            r_min = r_mid
        else:
            r_max = r_mid

    return max(0, r_min)

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

def repair_overlaps(circles):
    """Aggressively repair overlapping circles by shrinking radii."""
    for _ in range(50):
        conflicts = get_conflict_pairs(circles)
        if not conflicts:
            break

        for i, j, gap in conflicts:
            if gap < 0:
                # Shrink the larger or one proportionally
                shrink_factor = 0.98
                circles[i][2] *= shrink_factor
                circles[j][2] *= shrink_factor

    # Final cleanup
    for i in range(len(circles)):
        x, y, r = circles[i]
        r = min(r, x, 1 - x, y, 1 - y)
        circles[i][2] = max(0, r)

# ==============================================================================
# STEP 1: Generate multiple diverse initial placements
# ==============================================================================

all_placements = []

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
all_placements.append(circles_hex)

# Strategy B: Adaptive grid with random perturbation
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
all_placements.append(circles_grid)

# Strategy C: Radial/spiral placement
circles_spiral = []
center_x, center_y = 0.5, 0.5
for i in range(26):
    angle = 2 * math.pi * i / 26.0 + random.uniform(-0.1, 0.1)
    # Use varying radius to fill the space better
    r_spiral = 0.25 + 0.15 * (i / 26.0)
    x = center_x + r_spiral * math.cos(angle)
    y = center_y + r_spiral * math.sin(angle)

    x = max(0, min(1, x))
    y = max(0, min(1, y))

    circles_spiral.append([x, y, 0.01])

circles_spiral = circles_spiral[:26]
all_placements.append(circles_spiral)

# Strategy D: Clustered placement
circles_cluster = []
num_clusters = 4
circles_per_cluster = 26 // num_clusters + 1

for cluster_id in range(num_clusters):
    cluster_x = 0.3 + 0.4 * (cluster_id % 2)
    cluster_y = 0.3 + 0.4 * (cluster_id // 2)

    for i in range(circles_per_cluster):
        if len(circles_cluster) >= 26:
            break

        x = cluster_x + random.uniform(-0.15, 0.15)
        y = cluster_y + random.uniform(-0.15, 0.15)

        x = max(0, min(1, x))
        y = max(0, min(1, y))

        circles_cluster.append([x, y, 0.01])

circles_cluster = circles_cluster[:26]
all_placements.append(circles_cluster)

best_overall = None
best_score = -1

# ==============================================================================
# Optimize each placement strategy
# ==============================================================================

for strategy_idx, strategy_circles in enumerate(all_placements):
    circles = [c[:] for c in strategy_circles]

    # ==============================================================================
    # STEP 2: Aggressive radius growth with binary search
    # ==============================================================================
    for iteration in range(2000):
        old_radii = [c[2] for c in circles]

        for i in range(26):
            max_r = get_max_radius_binary(circles[i][0], circles[i][1], circles, i)
            circles[i][2] = max_r

        new_radii = [c[2] for c in circles]
        max_delta = max(abs(new_radii[i] - old_radii[i]) for i in range(26)) if new_radii else 0

        if max_delta < 1e-11:
            break

    # ==============================================================================
    # STEP 3: Coarse position adjustment (large steps)
    # ==============================================================================
    for shift_iter in range(150):
        shifted = False
        for i in range(26):
            x, y, r = circles[i]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.015, -0.008, 0, 0.008, 0.015]:
                for dy in [-0.015, -0.008, 0, 0.008, 0.015]:
                    if dx == 0 and dy == 0:
                        continue

                    nx = x + dx
                    ny = y + dy

                    if 0 <= nx <= 1 and 0 <= ny <= 1:
                        nr = get_max_radius_binary(nx, ny, circles, i)
                        if nr > best_r + 1e-12:
                            best_r = nr
                            best_x = nx
                            best_y = ny
                            shifted = True

            circles[i] = [best_x, best_y, best_r]

        if not shifted:
            break

    # ==============================================================================
    # STEP 4: Aggressive conflict resolution
    # ==============================================================================
    for conflict_pass in range(5):
        conflicts = get_conflict_pairs(circles)
        if not conflicts:
            break

        conflicts.sort(key=lambda x: x[2])

        for i, j, gap in conflicts[:10]:
            # Try to move circle i
            x, y, r = circles[i]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.004, -0.002, 0, 0.002, 0.004]:
                for dy in [-0.004, -0.002, 0, 0.002, 0.004]:
                    if dx == 0 and dy == 0:
                        continue

                    nx = x + dx
                    ny = y + dy

                    if 0 <= nx <= 1 and 0 <= ny <= 1:
                        nr = get_max_radius_binary(nx, ny, circles, i)
                        if nr > best_r + 1e-12:
                            best_r = nr
                            best_x = nx
                            best_y = ny

            circles[i] = [best_x, best_y, best_r]

            # Try to move circle j
            x, y, r = circles[j]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.004, -0.002, 0, 0.002, 0.004]:
                for dy in [-0.004, -0.002, 0, 0.002, 0.004]:
                    if dx == 0 and dy == 0:
                        continue

                    nx = x + dx
                    ny = y + dy

                    if 0 <= nx <= 1 and 0 <= ny <= 1:
                        nr = get_max_radius_binary(nx, ny, circles, j)
                        if nr > best_r + 1e-12:
                            best_r = nr
                            best_x = nx
                            best_y = ny

            circles[j] = [best_x, best_y, best_r]

    # ==============================================================================
    # STEP 5: Medium-scale position adjustment
    # ==============================================================================
    for step_size in [0.010, 0.005]:
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
                            nr = get_max_radius_binary(nx, ny, circles, i)
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
    for step_size in [0.0025, 0.0015]:
        for shift_iter in range(80):
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
                            nr = get_max_radius_binary(nx, ny, circles, i)
                            if nr > best_r + 1e-12:
                                best_r = nr
                                best_x = nx
                                best_y = ny
                                shifted = True

                circles[i] = [best_x, best_y, best_r]

            if not shifted:
                break

    # ==============================================================================
    # STEP 7: Ultra-fine tuning
    # ==============================================================================
    for shift_iter in range(60):
        shifted = False
        for i in range(26):
            x, y, r = circles[i]
            best_r = r
            best_x, best_y = x, y

            for dx in [-0.001, 0, 0.001]:
                for dy in [-0.001, 0, 0.001]:
                    if dx == 0 and dy == 0:
                        continue

                    nx = x + dx
                    ny = y + dy

                    if 0 <= nx <= 1 and 0 <= ny <= 1:
                        nr = get_max_radius_binary(nx, ny, circles, i)
                        if nr > best_r + 1e-12:
                            best_r = nr
                            best_x = nx
                            best_y = ny
                            shifted = True

            circles[i] = [best_x, best_y, best_r]

        if not shifted:
            break

    # ==============================================================================
    # STEP 8: Final radius maximization
    # ==============================================================================
    for _ in range(300):
        changed = False
        for i in range(26):
            max_r = get_max_radius_binary(circles[i][0], circles[i][1], circles, i)
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

    repair_overlaps(circles)

    # Verify and compute score
    current_score = sum(c[2] for c in circles)
    if current_score > best_score:
        best_score = current_score
        best_overall = [c[:] for c in circles]

print(best_overall)
