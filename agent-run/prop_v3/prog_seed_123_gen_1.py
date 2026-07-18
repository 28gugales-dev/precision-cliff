import math
import random
import itertools

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

def is_valid(circles):
    """Verify all circles are valid"""
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

# Phase 1: Smart hexagonal-offset grid initialization
circles = []
positions = []

for j in range(5):
    for i in range(6):
        if len(positions) < 26:
            # Hexagonal offset for tighter packing
            x = (i + 0.5 + (0.25 if j % 2 else 0)) / 6.0
            y = (j + 0.5) / 5.0
            x = max(0.01, min(0.99, x))
            y = max(0.01, min(0.99, y))
            positions.append((x, y))

for x, y in positions:
    circles.append([x, y, 0.0])

# Phase 2: Aggressive iterative growth with many passes
for iteration in range(400):
    improved = False
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)

        if new_r > r + 1e-11:
            circles[i][2] = new_r
            improved = True

# Phase 3: Large-scale repositioning (high temperature search)
for iteration in range(250):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        best_config = [old_x, old_y, old_r]
        best_score = sum(c[2] for c in circles)

        # Large perturbations
        step_deltas = [-0.04, -0.03, -0.02, -0.01, -0.005, 0, 0.005, 0.01, 0.02, 0.03, 0.04]
        for dx in step_deltas:
            for dy in step_deltas:
                new_x = old_x + dx
                new_y = old_y + dy

                if new_x < 0.001 or new_x > 0.999:
                    continue
                if new_y < 0.001 or new_y > 0.999:
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

# Phase 4: Medium-scale local search
for iteration in range(150):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        best_config = [old_x, old_y, old_r]
        best_score = sum(c[2] for c in circles)

        step_deltas = [-0.015, -0.01, -0.005, -0.002, 0, 0.002, 0.005, 0.01, 0.015]
        for dx in step_deltas:
            for dy in step_deltas:
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

# Phase 5: Radius-only optimization (keep positions fixed, expand radii)
for iteration in range(200):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)
        if new_r > r + 1e-11:
            circles[i][2] = new_r

# Phase 6: Fine-grained small-scale repositioning
for iteration in range(150):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        best_config = [old_x, old_y, old_r]
        best_score = sum(c[2] for c in circles)

        step_deltas = [-0.008, -0.004, -0.002, -0.001, 0, 0.001, 0.002, 0.004, 0.008]
        for dx in step_deltas:
            for dy in step_deltas:
                new_x = old_x + dx
                new_y = old_y + dy

                if new_x < 1e-5 or new_x > 1.0 - 1e-5:
                    continue
                if new_y < 1e-5 or new_y > 1.0 - 1e-5:
                    continue

                other_circles = circles[:i] + circles[i+1:]
                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r > 1e-10:
                    new_score = best_score - old_r + new_r
                    if new_score > best_score + 1e-11:
                        best_config = [new_x, new_y, new_r]
                        best_score = new_score

        circles[i] = best_config

# Phase 7: Ultra-fine tuning with micro-movements
for iteration in range(100):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        best_config = [old_x, old_y, old_r]
        best_score = sum(c[2] for c in circles)

        for dx in [-0.003, -0.001, 0, 0.001, 0.003]:
            for dy in [-0.003, -0.001, 0, 0.001, 0.003]:
                new_x = old_x + dx
                new_y = old_y + dy

                if new_x < 1e-5 or new_x > 1.0 - 1e-5:
                    continue
                if new_y < 1e-5 or new_y > 1.0 - 1e-5:
                    continue

                other_circles = circles[:i] + circles[i+1:]
                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r > 1e-10:
                    new_score = best_score - old_r + new_r
                    if new_score > best_score + 1e-11:
                        best_config = [new_x, new_y, new_r]
                        best_score = new_score

        circles[i] = best_config

# Final radius expansion pass
for iteration in range(100):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)
        if new_r > r + 1e-11:
            circles[i][2] = new_r

# Final validation clamping
for circle in circles:
    circle[0] = max(circle[2], min(1.0 - circle[2], circle[0]))
    circle[1] = max(circle[2], min(1.0 - circle[2], circle[1]))
    other = [c for c in circles if c is not circle]
    circle[2] = min(circle[2], get_max_radius(circle[0], circle[1], other))

print(circles)
