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

# Phase 0: Improved initialization with better grid coverage
circles = []

# Use a smarter grid placement - try to distribute 26 circles optimally
# 26 = 13*2, so we could do 13x2, or try different arrangements
# Let's use a quasi-hexagonal arrangement with perturbation

# Generate positions in a way that tries to spread them evenly
positions = []

# First, try a 5x6 grid with offset rows (hexagonal-like)
row_count = 6
col_count = 5
idx = 0

for i in range(col_count):
    for j in range(row_count):
        if idx < 26:
            # Offset every other row for better packing
            x_offset = 0.05 if j % 2 == 1 else 0
            x = (i + 0.5) / col_count + x_offset / col_count
            y = (j + 0.5) / row_count

            # Add some smart perturbation based on grid position
            x += random.uniform(-0.08, 0.08) / col_count
            y += random.uniform(-0.08, 0.08) / row_count

            # Clamp to safe range
            x = max(0.01, min(0.99, x))
            y = max(0.01, min(0.99, y))

            circles.append([x, y, 0.0])
            idx += 1

# Phase 1: Multi-iteration aggressive radius growth
for iteration in range(400):
    improved = False

    # Two-pass strategy: first expand all, then check for conflicts
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)

        if new_r > r + 1e-11:
            circles[i][2] = new_r
            improved = True

    if not improved and iteration > 120:
        break

# Phase 2: Coordinated repositioning with multi-scale approach
scales = [0.04, 0.02, 0.01, 0.005]

for scale_idx, step_scale in enumerate(scales):
    # More iterations for coarser scales, fewer for fine scales
    iterations = 200 - scale_idx * 45

    for iteration in range(iterations):
        best_overall_score = compute_score(circles)
        improved_any = False

        for i in range(26):
            old_x, old_y, old_r = circles[i]
            best_config = [old_x, old_y, old_r]
            best_score = best_overall_score

            # Adaptive search range based on scale
            search_range = 8 if scale_idx == 0 else (5 if scale_idx == 1 else (3 if scale_idx == 2 else 2))

            # Try different movement combinations
            for dx_idx in range(-search_range, search_range + 1):
                for dy_idx in range(-search_range, search_range + 1):
                    if dx_idx == 0 and dy_idx == 0:
                        continue

                    dx = dx_idx * step_scale / search_range
                    dy = dy_idx * step_scale / search_range
                    new_x = old_x + dx
                    new_y = old_y + dy

                    # Boundary check with margin
                    if new_x < 1e-4 or new_x > 1.0 - 1e-4:
                        continue
                    if new_y < 1e-4 or new_y > 1.0 - 1e-4:
                        continue

                    other_circles = circles[:i] + circles[i+1:]
                    new_r = get_max_radius(new_x, new_y, other_circles)

                    if new_r < 1e-11:
                        continue

                    # Score improvement for this circle
                    new_score = best_overall_score - old_r + new_r

                    if new_score > best_score + 1e-12:
                        best_score = new_score
                        best_config = [new_x, new_y, new_r]
                        improved_any = True

            if best_config != [old_x, old_y, old_r]:
                circles[i] = best_config
                best_overall_score = best_score

# Phase 3: Expansion and aggressive settling
for iteration in range(150):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        max_possible = get_max_radius(x, y, other_circles)
        if max_possible > r + 1e-12:
            circles[i][2] = max_possible

# Phase 4: Fine-tuning with very small moves
for iteration in range(100):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        best_config = [old_x, old_y, old_r]
        best_score = old_r

        # Very small step deltas
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

                if new_r > best_score + 1e-12:
                    best_score = new_r
                    best_config = [new_x, new_y, new_r]

        circles[i] = best_config

# Phase 5: Ultra-fine adjustments targeting slow-growing circles
# Identify circles that are smaller than average and give them special attention
avg_radius = compute_score(circles) / 26.0
small_circles = [i for i in range(26) if circles[i][2] < avg_radius * 0.85]

for _ in range(60):
    for i in small_circles:
        old_x, old_y, old_r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        best_config = [old_x, old_y, old_r]
        best_score = old_r

        # Very fine deltas for small circles
        deltas = [-0.002, -0.001, 0, 0.001, 0.002]

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

                if new_r > best_score + 1e-13:
                    best_score = new_r
                    best_config = [new_x, new_y, new_r]

        circles[i] = best_config

# Phase 6: Final validation and safe clamping
for circle in circles:
    # Ensure radius is valid
    if circle[2] < 0:
        circle[2] = 0

    # Ensure center respects radius constraint
    circle[0] = max(circle[2] + 1e-11, min(1.0 - circle[2] - 1e-11, circle[0]))
    circle[1] = max(circle[2] + 1e-11, min(1.0 - circle[2] - 1e-11, circle[1]))

    # Final radius check with all other circles
    other = [c for c in circles if c is not circle]
    max_r = get_max_radius(circle[0], circle[1], other)
    if max_r < circle[2]:
        circle[2] = max_r

print(circles)
