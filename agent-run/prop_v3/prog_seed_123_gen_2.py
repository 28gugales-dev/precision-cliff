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

# Better initialization: 5x6 grid (different orientation) with small perturbations
circles = []
positions = []

for i in range(5):
    for j in range(6):
        if len(positions) < 26:
            x = (i + 0.5) / 5.0
            y = (j + 0.5) / 6.0
            # Add small random perturbations to break symmetry
            x += random.uniform(-0.015, 0.015)
            y += random.uniform(-0.015, 0.015)
            # Clamp to valid range
            x = max(0.03, min(0.97, x))
            y = max(0.03, min(0.97, y))
            positions.append((x, y))

for x, y in positions:
    circles.append([x, y, 0.0])

# Phase 1: Aggressive radius growth
for _ in range(500):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)
        if new_r > r + 1e-11:
            circles[i][2] = new_r

# Phase 2: Radial push-out (repulsion to reduce crowding)
for iteration in range(80):
    for i in range(26):
        x, y, r = circles[i]

        # Compute repulsion forces from all other circles
        fx, fy = 0, 0
        for j in range(26):
            if i != j:
                cx, cy, cr = circles[j]
                d = distance((x, y), (cx, cy))
                if d > 1e-6:
                    # Repulsion direction (away from circle j)
                    dx = (x - cx) / d
                    dy = (y - cy) / d
                    # Weight inversely by distance to prioritize nearby circles
                    w = 1.0 / (d + 0.005)
                    fx += dx * w
                    fy += dy * w

        # Normalize force vector
        f_mag = math.sqrt(fx*fx + fy*fy)
        if f_mag > 1e-6:
            fx /= f_mag
            fy /= f_mag
            new_x = x + fx * 0.008
            new_y = y + fy * 0.008
        else:
            new_x, new_y = x, y

        # Keep within bounds with radius margin
        new_x = max(r + 0.001, min(1.0 - r - 0.001, new_x))
        new_y = max(r + 0.001, min(1.0 - r - 0.001, new_y))

        circles[i][0] = new_x
        circles[i][1] = new_y

# Phase 3: Regrow radii after repositioning
for _ in range(400):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)
        if new_r > r + 1e-11:
            circles[i][2] = new_r

# Phase 4: Comprehensive directional local search
for iteration in range(250):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        best_config = [old_x, old_y, old_r]
        best_score = old_r

        # Try 12 directional angles with multiple distances
        for angle_idx in range(12):
            angle = 2 * math.pi * angle_idx / 12
            for step_dist in [0.003, 0.007, 0.012, 0.018]:
                dx = step_dist * math.cos(angle)
                dy = step_dist * math.sin(angle)

                new_x = old_x + dx
                new_y = old_y + dy

                # Boundary check
                if new_x - best_config[2] < 1e-5 or new_x + best_config[2] > 1.0 - 1e-5:
                    continue
                if new_y - best_config[2] < 1e-5 or new_y + best_config[2] > 1.0 - 1e-5:
                    continue

                other_circles = circles[:i] + circles[i+1:]
                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r > best_score + 1e-11:
                    best_score = new_r
                    best_config = [new_x, new_y, new_r]

        circles[i] = best_config

# Phase 5: Fine-grained directional tuning
for iteration in range(100):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        best_config = [old_x, old_y, old_r]
        best_score = old_r

        for angle_idx in range(20):
            angle = 2 * math.pi * angle_idx / 20
            for fine_dist in [0.0005, 0.001, 0.0015, 0.002]:
                dx = fine_dist * math.cos(angle)
                dy = fine_dist * math.sin(angle)

                new_x = old_x + dx
                new_y = old_y + dy

                if new_x - best_config[2] < 1e-5 or new_x + best_config[2] > 1.0 - 1e-5:
                    continue
                if new_y - best_config[2] < 1e-5 or new_y + best_config[2] > 1.0 - 1e-5:
                    continue

                other_circles = circles[:i] + circles[i+1:]
                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r > best_score + 1e-12:
                    best_score = new_r
                    best_config = [new_x, new_y, new_r]

        circles[i] = best_config

# Phase 6: Ultra-fine optimization with reduced step sizes
for iteration in range(50):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        best_config = [old_x, old_y, old_r]
        best_score = old_r

        for angle_idx in range(16):
            angle = 2 * math.pi * angle_idx / 16
            for tiny_dist in [0.0001, 0.00025]:
                dx = tiny_dist * math.cos(angle)
                dy = tiny_dist * math.sin(angle)

                new_x = old_x + dx
                new_y = old_y + dy

                if new_x - best_config[2] < 1e-5 or new_x + best_config[2] > 1.0 - 1e-5:
                    continue
                if new_y - best_config[2] < 1e-5 or new_y + best_config[2] > 1.0 - 1e-5:
                    continue

                other_circles = circles[:i] + circles[i+1:]
                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r > best_score + 1e-13:
                    best_score = new_r
                    best_config = [new_x, new_y, new_r]

        circles[i] = best_config

# Final safety clamping to ensure validity
for circle in circles:
    circle[0] = max(circle[2], min(1.0 - circle[2], circle[0]))
    circle[1] = max(circle[2], min(1.0 - circle[2], circle[1]))
    other = [c for c in circles if c is not circle]
    circle[2] = min(circle[2], get_max_radius(circle[0], circle[1], other))

print(circles)
