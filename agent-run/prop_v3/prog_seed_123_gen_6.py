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

# Phase 0: Improved initialization with better jitter distribution
circles = []

# Use 6x5 grid base with improved randomized perturbations
for i in range(6):
    for j in range(5):
        if len(circles) < 26:
            # Grid position with better jitter control
            x = (i + 0.5) / 6.0 + random.uniform(-0.125, 0.125) / 6.0
            y = (j + 0.5) / 5.0 + random.uniform(-0.125, 0.125) / 5.0

            # Clamp to safe range
            x = max(0.02, min(0.98, x))
            y = max(0.02, min(0.98, y))
            circles.append([x, y, 0.0])

# Phase 1: Aggressive radius growth with improved convergence detection
no_improve_count = 0
for iteration in range(420):
    improved = False
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)

        if new_r > r + 1e-10:
            circles[i][2] = new_r
            improved = True

    # Track consecutive iterations with no improvement for early exit
    if not improved:
        no_improve_count += 1
        if no_improve_count > 100:
            break
    else:
        no_improve_count = 0

# Phase 2: Enhanced multi-scale local repositioning with adaptive parameters
# More iterations at finer scales where gains are possible
scales = [0.036, 0.018, 0.009, 0.0045]
iterations_per_scale = [200, 190, 170, 120]

for scale_idx, (step_scale, iterations) in enumerate(zip(scales, iterations_per_scale)):
    for iteration in range(iterations):
        for i in range(26):
            old_x, old_y, old_r = circles[i]
            best_config = [old_x, old_y, old_r]
            best_score = compute_score(circles)

            # Adaptive neighbor search based on scale
            search_range = 8 if scale_idx <= 1 else 6

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

# Phase 3: Aggressive expansion and settling phase
for iteration in range(150):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]

        # Try to grow the radius aggressively
        max_possible = get_max_radius(x, y, other_circles)
        if max_possible > r + 1e-11:
            circles[i][2] = max_possible

# Phase 4: Fine micro-adjustments with optimized deltas
for iteration in range(120):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        best_config = [old_x, old_y, old_r]

        # Try very small moves with refined step sizes
        deltas = [-0.0035, -0.0015, 0, 0.0015, 0.0035]

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
