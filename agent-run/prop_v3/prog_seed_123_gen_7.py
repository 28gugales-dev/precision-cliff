import math
import random

random.seed(123)

def distance(c1, c2):
    """Euclidean distance between two points"""
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

def get_max_radius(x, y, circles):
    """Get maximum radius for a circle at (x, y) without overlap or boundary violation"""
    r_max = min(x, 1.0 - x, y, 1.0 - y)
    for cx, cy, cr in circles:
        d = distance((x, y), (cx, cy))
        if d < 1e-10:
            return 0
        r_max = min(r_max, d - cr)
    return max(0, r_max)

def compute_score(circles):
    """Compute total score (sum of all radii)"""
    return sum(c[2] for c in circles)

# Phase 0: Improved initialization with multiple strategies
circles = []

# Grid-based initialization with better jitter control
for i in range(6):
    for j in range(5):
        if len(circles) < 26:
            x = (i + 0.5) / 6.0 + random.uniform(-0.11, 0.11) / 6.0
            y = (j + 0.5) / 5.0 + random.uniform(-0.11, 0.11) / 5.0
            x = max(0.02, min(0.98, x))
            y = max(0.02, min(0.98, y))
            circles.append([x, y, 0.0])

# Phase 1: Super-aggressive radius growth with more iterations
for iteration in range(600):
    improved = False
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)

        if new_r > r + 1e-10:
            circles[i][2] = new_r
            improved = True

    if not improved and iteration > 120:
        break

# Phase 2: Multi-scale local repositioning optimization with finer scales
scales = [0.04, 0.022, 0.012, 0.006, 0.003]

for scale_idx, step_scale in enumerate(scales):
    iterations = 240 - scale_idx * 35

    for iteration in range(iterations):
        for i in range(26):
            old_x, old_y, old_r = circles[i]
            best_config = [old_x, old_y, old_r]
            best_score = compute_score(circles)

            search_range = 8 - scale_idx if scale_idx < 4 else 3

            for dx_idx in range(-search_range, search_range + 1):
                for dy_idx in range(-search_range, search_range + 1):
                    if dx_idx == 0 and dy_idx == 0:
                        continue

                    dx = dx_idx * step_scale / search_range
                    dy = dy_idx * step_scale / search_range
                    new_x = old_x + dx
                    new_y = old_y + dy

                    if new_x < 1e-4 or new_x > 1.0 - 1e-4:
                        continue
                    if new_y < 1e-4 or new_y > 1.0 - 1e-4:
                        continue

                    other_circles = circles[:i] + circles[i+1:]
                    new_r = get_max_radius(new_x, new_y, other_circles)

                    if new_r < 1e-10:
                        continue

                    new_score = best_score - old_r + new_r

                    if new_score > best_score + 1e-11:
                        best_score = new_score
                        best_config = [new_x, new_y, new_r]

            circles[i] = best_config

# Phase 3: Aggressive expansion and settling
for iteration in range(180):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        max_possible = get_max_radius(x, y, other_circles)
        if max_possible > r + 1e-11:
            circles[i][2] = max_possible

# Phase 4: Close-pair optimization - improve nearby circles together
for iteration in range(100):
    for i in range(26):
        for j in range(i+1, 26):
            dist = distance((circles[i][0], circles[i][1]), (circles[j][0], circles[j][1]))

            # Only optimize if circles are relatively close
            if dist > 0.6:
                continue

            xi, yi, ri = circles[i]
            xj, yj, rj = circles[j]

            # Compute direction away from each other
            if dist > 1e-9:
                dx_dir = (xj - xi) / dist
                dy_dir = (yj - yi) / dist
            else:
                dx_dir, dy_dir = 1, 0

            # Try small moves away from each other
            for step in [-0.004, -0.002, 0.002, 0.004]:
                new_xi = xi - dx_dir * step
                new_yi = yi - dy_dir * step
                new_xj = xj + dx_dir * step
                new_yj = yj + dy_dir * step

                # Boundary check
                if (new_xi < 1e-5 or new_xi > 1.0 - 1e-5 or
                    new_yi < 1e-5 or new_yi > 1.0 - 1e-5 or
                    new_xj < 1e-5 or new_xj > 1.0 - 1e-5 or
                    new_yj < 1e-5 or new_yj > 1.0 - 1e-5):
                    continue

                # Compute max radii for new positions
                others_i = circles[:i] + circles[i+1:]
                others_j = circles[:j] + circles[j+1:]

                new_ri = get_max_radius(new_xi, new_yi, others_i)
                new_rj = get_max_radius(new_xj, new_yj, others_j)

                # Only accept if total radius increases
                if new_ri + new_rj > ri + rj + 1e-11:
                    circles[i] = [new_xi, new_yi, new_ri]
                    circles[j] = [new_xj, new_yj, new_rj]

# Phase 5: Ultra-fine micro-adjustments with expanded search
for iteration in range(150):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        best_config = [old_x, old_y, old_r]

        deltas = [-0.005, -0.003, -0.001, 0, 0.001, 0.003, 0.005]

        for dx in deltas:
            for dy in deltas:
                if dx == 0 and dy == 0:
                    continue

                new_x = old_x + dx
                new_y = old_y + dy

                if new_x < 1e-5 or new_x > 1.0 - 1e-5:
                    continue
                if new_y < 1e-5 or new_y > 1.0 - 1e-5:
                    continue

                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r > best_config[2] + 1e-11:
                    best_config = [new_x, new_y, new_r]

        circles[i] = best_config

# Phase 6: Final validation and clamping
for circle in circles:
    # Ensure center is positioned safely
    circle[0] = max(circle[2] + 1e-10, min(1.0 - circle[2] - 1e-10, circle[0]))
    circle[1] = max(circle[2] + 1e-10, min(1.0 - circle[2] - 1e-10, circle[1]))

    # Ensure radius doesn't violate any constraints
    other = [c for c in circles if c is not circle]
    circle[2] = min(circle[2], get_max_radius(circle[0], circle[1], other))

print(circles)
