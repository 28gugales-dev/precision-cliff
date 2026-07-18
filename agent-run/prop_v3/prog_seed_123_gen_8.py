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

# Phase 0: Smart initialization - select best 26 positions from larger candidate pool
candidate_positions = []

# Generate 40 candidate positions using improved grid + random
for i in range(7):
    for j in range(6):
        if len(candidate_positions) < 40:
            # Add jitter to grid positions
            x = (i + 0.5) / 7.0 + random.uniform(-0.1, 0.1) / 7.0
            y = (j + 0.5) / 6.0 + random.uniform(-0.1, 0.1) / 6.0
            x = max(0.02, min(0.98, x))
            y = max(0.02, min(0.98, y))
            candidate_positions.append((x, y))

# Score each candidate based on potential radius
scored_positions = []
for x, y in candidate_positions:
    # Boundary potential
    boundary_potential = min(x, 1.0 - x, y, 1.0 - y)
    scored_positions.append((boundary_potential, x, y))

# Sort by boundary potential (descending) and select top 26
scored_positions.sort(reverse=True)
circles = [[x, y, 0.0] for _, x, y in scored_positions[:26]]

# Phase 1: Aggressive radius growth - many iterations for maximum expansion
for iteration in range(600):
    improved = False
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)

        if new_r > r + 1e-10:
            circles[i][2] = new_r
            improved = True

    # Early exit if no improvement
    if not improved and iteration > 200:
        break

# Phase 2: Multi-scale local repositioning with aggressive search
scales = [0.05, 0.025, 0.012, 0.006, 0.003]

for scale_idx, step_scale in enumerate(scales):
    iterations = 280 - scale_idx * 40

    for iteration in range(iterations):
        improved_this_iteration = False

        for i in range(26):
            old_x, old_y, old_r = circles[i]
            best_config = [old_x, old_y, old_r]
            best_score = compute_score(circles)

            # Adaptive neighbor search with larger range
            search_range = 11 if scale_idx == 0 else (9 if scale_idx == 1 else (7 if scale_idx == 2 else 5))

            for dx_idx in range(-search_range, search_range + 1):
                for dy_idx in range(-search_range, search_range + 1):
                    if dx_idx == 0 and dy_idx == 0:
                        continue

                    dx = dx_idx * step_scale / search_range
                    dy = dy_idx * step_scale / search_range
                    new_x = old_x + dx
                    new_y = old_y + dy

                    # Boundary check with tighter tolerance
                    if new_x < 1e-5 or new_x > 1.0 - 1e-5:
                        continue
                    if new_y < 1e-5 or new_y > 1.0 - 1e-5:
                        continue

                    other_circles = circles[:i] + circles[i+1:]
                    new_r = get_max_radius(new_x, new_y, other_circles)

                    if new_r < 1e-10:
                        continue

                    # Compute new total score
                    new_score = best_score - old_r + new_r

                    if new_score > best_score + 1e-12:
                        best_score = new_score
                        best_config = [new_x, new_y, new_r]
                        improved_this_iteration = True

            circles[i] = best_config

        # Early exit if no improvement found
        if not improved_this_iteration and iteration > iterations // 2:
            break

# Phase 3: Aggressive expansion and settling phase
for iteration in range(200):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]

        # Try to grow the radius aggressively
        max_possible = get_max_radius(x, y, other_circles)
        if max_possible > r + 1e-11:
            circles[i][2] = max_possible

# Phase 4: Fine micro-adjustments with extended search
for iteration in range(120):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        best_config = [old_x, old_y, old_r]

        # Try small moves in multiple directions
        deltas = [-0.004, -0.002, -0.001, 0, 0.001, 0.002, 0.004]

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

# Phase 5: Final expansion pass to capture any remaining potential
for iteration in range(100):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        max_possible = get_max_radius(x, y, other_circles)
        if max_possible > r + 1e-11:
            circles[i][2] = max_possible

# Phase 6: Final validation and clamping
for circle in circles:
    # Ensure center is positioned safely within bounds
    circle[0] = max(circle[2] + 1e-10, min(1.0 - circle[2] - 1e-10, circle[0]))
    circle[1] = max(circle[2] + 1e-10, min(1.0 - circle[2] - 1e-10, circle[1]))

    # Ensure radius doesn't violate any constraints
    other = [c for c in circles if c is not circle]
    circle[2] = min(circle[2], get_max_radius(circle[0], circle[1], other))

print(circles)
