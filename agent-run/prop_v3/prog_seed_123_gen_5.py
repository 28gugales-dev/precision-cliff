import math
import random

random.seed(123)

def distance(c1, c2):
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

def get_max_radius(x, y, circles):
    """Get maximum radius for circle at (x, y) without overlap or boundary violation"""
    r_max = min(x, 1.0 - x, y, 1.0 - y)
    for cx, cy, cr in circles:
        d = distance((x, y), (cx, cy))
        if d < 1e-10:
            return 0
        r_max = min(r_max, d - cr)
    return max(0, r_max)

def compute_score(circles):
    return sum(c[2] for c in circles)

# Better initialization using optimized row-based layout for 26 circles
circles = []
random_state = random.random()  # consume for reproducibility

# Create 26 circles with optimized spacing: 5+5+5+5+6 layout
y_coords = [0.12, 0.3, 0.5, 0.7, 0.88]
x_per_row = [5, 5, 5, 5, 6]

circle_idx = 0
for row, (y_base, count) in enumerate(zip(y_coords, x_per_row)):
    for i in range(count):
        # Better spacing: vary x spacing based on row count
        x = (i + 0.5) / count
        # Add controlled jitter
        x += random.uniform(-0.08, 0.08) / count
        y = y_base + random.uniform(-0.05, 0.05)

        # Clamp to safe interior
        x = max(0.015, min(0.985, x))
        y = max(0.015, min(0.985, y))
        circles.append([x, y, 0.0])
        circle_idx += 1

# Phase 1: Aggressive greedy radius growth (more iterations for better coverage)
for iteration in range(750):
    improved = False
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)

        if new_r > r + 1e-11:
            circles[i][2] = new_r
            improved = True

    if not improved and iteration > 150:
        break

# Phase 2: Multi-scale position optimization with adaptive search
scales = [0.032, 0.016, 0.008, 0.004]

for scale_idx, step_scale in enumerate(scales):
    iterations = 220 - scale_idx * 35
    search_range = 6 - scale_idx

    for iteration in range(iterations):
        for i in range(26):
            old_x, old_y, old_r = circles[i]
            best_config = [old_x, old_y, old_r]

            other_circles = circles[:i] + circles[i+1:]

            # Adaptive neighbor search with grid pattern
            for dx_idx in range(-search_range, search_range + 1):
                for dy_idx in range(-search_range, search_range + 1):
                    if dx_idx == 0 and dy_idx == 0:
                        continue

                    dx = (dx_idx * step_scale) / search_range
                    dy = (dy_idx * step_scale) / search_range
                    new_x = old_x + dx
                    new_y = old_y + dy

                    # Boundary check with tolerance
                    if new_x < 1e-4 or new_x > 1.0 - 1e-4:
                        continue
                    if new_y < 1e-4 or new_y > 1.0 - 1e-4:
                        continue

                    new_r = get_max_radius(new_x, new_y, other_circles)

                    if new_r > best_config[2] + 1e-12:
                        best_config = [new_x, new_y, new_r]

            circles[i] = best_config

# Phase 3: Expansion and settling phase with aggressive growth
for iteration in range(180):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]

        max_possible = get_max_radius(x, y, other_circles)
        if max_possible > r + 1e-12:
            circles[i][2] = max_possible

# Phase 4: Hybrid micro-adjustment with combined position and radius optimization
micro_steps = [-0.005, -0.002, 0, 0.002, 0.005]

for iteration in range(150):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        best_config = [old_x, old_y, old_r]

        other_circles = circles[:i] + circles[i+1:]

        for dx in micro_steps:
            for dy in micro_steps:
                if dx == 0 and dy == 0:
                    continue

                new_x = old_x + dx
                new_y = old_y + dy

                if new_x < 1e-5 or new_x > 1.0 - 1e-5:
                    continue
                if new_y < 1e-5 or new_y > 1.0 - 1e-5:
                    continue

                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r > best_config[2] + 1e-12:
                    best_config = [new_x, new_y, new_r]

        circles[i] = best_config

# Phase 5: Ultra-fine adjustments with systematic perturbations
for iteration in range(100):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)

        if new_r > r + 1e-13:
            circles[i][2] = new_r

# Phase 6: Final validation and clamping with safe margins
for circle in circles:
    # Clamp center position with safety margin
    circle[0] = max(circle[2] + 1e-10, min(1.0 - circle[2] - 1e-10, circle[0]))
    circle[1] = max(circle[2] + 1e-10, min(1.0 - circle[2] - 1e-10, circle[1]))

    # Ensure radius doesn't violate constraints
    other = [c for c in circles if c is not circle]
    max_r = get_max_radius(circle[0], circle[1], other)
    circle[2] = min(circle[2], max_r)

print(circles)
