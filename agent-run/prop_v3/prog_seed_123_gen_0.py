import math
import random
import itertools

random.seed(123)

def distance(c1, c2):
    """Euclidean distance between two points"""
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

def get_max_radius(x, y, circles):
    """Get maximum radius for a circle at (x, y) without overlap or boundary violation"""
    # Constraint from square boundaries
    r_max = min(x, 1.0 - x, y, 1.0 - y)

    # Constraint from existing circles (no overlap)
    for cx, cy, cr in circles:
        d = distance((x, y), (cx, cy))
        if d < 1e-10:
            return 0  # Same position, cannot place
        # Distance between centers must be >= r + cr
        r_max = min(r_max, d - cr)

    return max(0, r_max)

def is_valid(circles):
    """Verify all circles are valid (within bounds, no overlaps)"""
    for i, (x, y, r) in enumerate(circles):
        if x - r < -1e-9 or x + r > 1.0 + 1e-9:
            return False
        if y - r < -1e-9 or y + r > 1.0 + 1e-9:
            return False
        for j, (cx, cy, cr) in enumerate(circles):
            if i < j:
                d = distance((x, y), (cx, cy))
                if d < r + cr - 1e-9:
                    return False
    return True

# Phase 1: Initialize with grid placement
circles = []
positions = []

# Use a 6x5 grid as baseline, then optimize
for i in range(6):
    for j in range(5):
        if len(positions) < 26:
            x = (i + 0.5) / 6.0
            y = (j + 0.5) / 5.0
            positions.append((x, y))

for x, y in positions:
    circles.append([x, y, 0.0])

# Phase 2: Grow circles iteratively to maximum size
for iteration in range(200):
    improved = False
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)

        if new_r > r + 1e-10:
            circles[i][2] = new_r
            improved = True

# Phase 3: Local repositioning with radius optimization
for iteration in range(100):
    total_radius = sum(c[2] for c in circles)

    for i in range(26):
        old_x, old_y, old_r = circles[i]
        best_config = [old_x, old_y, old_r]
        best_score = total_radius

        # Try nearby positions
        for dx in [-0.02, -0.01, -0.005, 0, 0.005, 0.01, 0.02]:
            for dy in [-0.02, -0.01, -0.005, 0, 0.005, 0.01, 0.02]:
                new_x = old_x + dx
                new_y = old_y + dy

                # Check bounds
                if new_x < 1e-4 or new_x > 1.0 - 1e-4:
                    continue
                if new_y < 1e-4 or new_y > 1.0 - 1e-4:
                    continue

                # Get max radius at new position
                other_circles = circles[:i] + circles[i+1:]
                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r < 1e-10:
                    continue

                # Compute new total score
                new_score = total_radius - old_r + new_r

                if new_score > best_score + 1e-10:
                    best_score = new_score
                    best_config = [new_x, new_y, new_r]

        circles[i] = best_config

# Phase 4: Fine-grained optimization with micro-movements
for iteration in range(50):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        best_config = [old_x, old_y, old_r]
        best_score = sum(c[2] for c in circles)

        # Try smaller perturbations
        for dx in [-0.005, -0.002, 0, 0.002, 0.005]:
            for dy in [-0.005, -0.002, 0, 0.002, 0.005]:
                new_x = old_x + dx
                new_y = old_y + dy

                if new_x < 1e-5 or new_x > 1.0 - 1e-5:
                    continue
                if new_y < 1e-5 or new_y > 1.0 - 1e-5:
                    continue

                other_circles = circles[:i] + circles[i+1:]
                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r > old_r + 1e-10:
                    circles[i] = [new_x, new_y, new_r]
                    new_score = sum(c[2] for c in circles)
                    if new_score > best_score:
                        best_score = new_score
                        best_config = circles[i][:]
                    else:
                        circles[i] = [old_x, old_y, old_r]

        circles[i] = best_config

# Clamp to ensure validity
for circle in circles:
    circle[0] = max(circle[2], min(1.0 - circle[2], circle[0]))
    circle[1] = max(circle[2], min(1.0 - circle[2], circle[1]))
    other = [c for c in circles if c is not circle]
    circle[2] = min(circle[2], get_max_radius(circle[0], circle[1], other))

print(circles)
