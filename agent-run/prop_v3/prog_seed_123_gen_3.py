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

# Phase 0: Improved initialization with stratified jitter
circles = []
random_jitter = random.random()  # For reproducibility with seed

# Use 6x5 grid base with randomized perturbations
for i in range(6):
    for j in range(5):
        if len(circles) < 26:
            # Grid position with controlled randomization
            x = (i + 0.5) / 6.0 + random.uniform(-0.12, 0.12) / 6.0
            y = (j + 0.5) / 5.0 + random.uniform(-0.12, 0.12) / 5.0

            # Clamp to safe range
            x = max(0.02, min(0.98, x))
            y = max(0.02, min(0.98, y))
            circles.append([x, y, 0.0])

# Phase 1: Aggressive radius growth (more iterations than champion)
for iteration in range(350):
    improved = False
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)

        if new_r > r + 1e-10:
            circles[i][2] = new_r
            improved = True

    # Early exit if no improvement
    if not improved and iteration > 100:
        break

# Phase 2: Multi-scale local repositioning optimization
# Use decreasing step sizes for finer control
scales = [0.035, 0.018, 0.009]

for scale_idx, step_scale in enumerate(scales):
    iterations = 180 - scale_idx * 40  # More iterations at coarser scales

    for iteration in range(iterations):
        for i in range(26):
            old_x, old_y, old_r = circles[i]
            best_config = [old_x, old_y, old_r]
            best_score = compute_score(circles)

            # Adaptive neighbor search
            search_range = 7 if scale_idx == 0 else (5 if scale_idx == 1 else 3)

            for dx_idx in range(-search_range, search_range + 1):
                for dy_idx in range(-search_range, search_range + 1):
                    if dx_idx == 0 and dy_idx == 0:
                        continue

                    dx = dx_idx * step_scale / search_range
                    dy = dy_idx * step_scale / search_range
                    new_x = old_x + dx
                    new_y = old_y + dy

                    # Boundary check
                    if new_x < 1e-4 or new_x > 1.0 - 1e-4:
                        continue
                    if new_y < 1e-4 or new_y > 1.0 - 1e-4:
                        continue

                    other_circles = circles[:i] + circles[i+1:]
                    new_r = get_max_radius(new_x, new_y, other_circles)

                    if new_r < 1e-10:
                        continue

                    # Compute new total score
                    new_score = best_score - old_r + new_r

                    if new_score > best_score + 1e-11:
                        best_score = new_score
                        best_config = [new_x, new_y, new_r]

            circles[i] = best_config

# Phase 3: Expansion and settling phase
for iteration in range(120):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]

        # Try to grow the radius aggressively
        max_possible = get_max_radius(x, y, other_circles)
        if max_possible > r + 1e-11:
            circles[i][2] = max_possible

# Phase 4: Fine micro-adjustments with combined moves
for iteration in range(80):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        best_config = [old_x, old_y, old_r]

        # Try very small moves combined with growth
        deltas = [-0.003, -0.001, 0, 0.001, 0.003]

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

# Phase 5: Final validation and clamping
for circle in circles:
    # Ensure center is positioned safely
    circle[0] = max(circle[2] + 1e-10, min(1.0 - circle[2] - 1e-10, circle[0]))
    circle[1] = max(circle[2] + 1e-10, min(1.0 - circle[2] - 1e-10, circle[1]))

    # Ensure radius doesn't violate any constraints
    other = [c for c in circles if c is not circle]
    circle[2] = min(circle[2], get_max_radius(circle[0], circle[1], other))

print(circles)
