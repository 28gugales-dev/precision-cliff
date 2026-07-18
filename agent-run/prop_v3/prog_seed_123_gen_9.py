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

def check_valid(circles):
    """Verify all circles are valid"""
    for i, (x, y, r) in enumerate(circles):
        if x - r < -1e-8 or x + r > 1.0 + 1e-8:
            return False
        if y - r < -1e-8 or y + r > 1.0 + 1e-8:
            return False
        for j in range(i+1, len(circles)):
            cx, cy, cr = circles[j]
            d = distance((x, y), (cx, cy))
            if d < r + cr - 1e-8:
                return False
    return True

# Phase 0: Multiple initialization attempts - use best one
best_init_circles = None
best_init_score = -1

# Strategy 1: 6x5 grid with optimized jitter
for attempt in range(1):
    circles = []
    for i in range(6):
        for j in range(5):
            if len(circles) < 26:
                # Grid position with controlled randomization
                x = (i + 0.5) / 6.0 + random.uniform(-0.08, 0.08) / 6.0
                y = (j + 0.5) / 5.0 + random.uniform(-0.08, 0.08) / 5.0
                x = max(0.02, min(0.98, x))
                y = max(0.02, min(0.98, y))
                circles.append([x, y, 0.0])

    # Quick growth pass for initialization evaluation
    for _ in range(50):
        for i in range(26):
            x, y, r = circles[i]
            other_circles = circles[:i] + circles[i+1:]
            new_r = get_max_radius(x, y, other_circles)
            if new_r > r:
                circles[i][2] = new_r

    init_score = compute_score(circles)
    if init_score > best_init_score:
        best_init_score = init_score
        best_init_circles = [c[:] for c in circles]

circles = best_init_circles

# Phase 1: Very aggressive radius growth with better convergence
for iteration in range(400):
    improved = False
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)

        if new_r > r + 1e-11:
            circles[i][2] = new_r
            improved = True

    if not improved and iteration > 80:
        break

# Phase 2: Enhanced multi-scale local repositioning with finer scales
scales = [0.04, 0.02, 0.01, 0.005]

for scale_idx, step_scale in enumerate(scales):
    iterations = 200 - scale_idx * 40

    for iteration in range(iterations):
        for i in range(26):
            old_x, old_y, old_r = circles[i]
            best_config = [old_x, old_y, old_r]
            best_score = compute_score(circles)

            # Adaptive neighbor search
            search_range = 8 if scale_idx == 0 else (6 if scale_idx == 1 else (4 if scale_idx == 2 else 3))

            for dx_idx in range(-search_range, search_range + 1):
                for dy_idx in range(-search_range, search_range + 1):
                    if dx_idx == 0 and dy_idx == 0:
                        continue

                    dx = dx_idx * step_scale / search_range
                    dy = dy_idx * step_scale / search_range
                    new_x = old_x + dx
                    new_y = old_y + dy

                    if new_x < 1e-5 or new_x > 1.0 - 1e-5:
                        continue
                    if new_y < 1e-5 or new_y > 1.0 - 1e-5:
                        continue

                    other_circles = circles[:i] + circles[i+1:]
                    new_r = get_max_radius(new_x, new_y, other_circles)

                    if new_r < 1e-11:
                        continue

                    new_score = best_score - old_r + new_r

                    if new_score > best_score + 1e-12:
                        best_score = new_score
                        best_config = [new_x, new_y, new_r]

            circles[i] = best_config

# Phase 3: Intensive expansion and settling
for iteration in range(150):
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        max_possible = get_max_radius(x, y, other_circles)
        if max_possible > r + 1e-12:
            circles[i][2] = max_possible

# Phase 4: Aggressive fine adjustments with tighter deltas
for iteration in range(120):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        best_config = [old_x, old_y, old_r]

        deltas = [-0.004, -0.002, -0.001, 0, 0.001, 0.002, 0.004]

        for dx in deltas:
            for dy in deltas:
                if dx == 0 and dy == 0:
                    continue

                new_x = old_x + dx
                new_y = old_y + dy

                if new_x < 1e-6 or new_x > 1.0 - 1e-6:
                    continue
                if new_y < 1e-6 or new_y > 1.0 - 1e-6:
                    continue

                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r > best_config[2] + 1e-12:
                    best_config = [new_x, new_y, new_r]

        circles[i] = best_config

# Phase 5: Secondary aggressive growth pass
for iteration in range(200):
    improved = False
    for i in range(26):
        x, y, r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        new_r = get_max_radius(x, y, other_circles)
        if new_r > r + 1e-12:
            circles[i][2] = new_r
            improved = True
    if not improved and iteration > 50:
        break

# Phase 6: Ultra-fine micro-adjustments
for iteration in range(80):
    for i in range(26):
        old_x, old_y, old_r = circles[i]
        other_circles = circles[:i] + circles[i+1:]
        best_config = [old_x, old_y, old_r]

        for dx in [-0.0015, -0.0005, 0, 0.0005, 0.0015]:
            for dy in [-0.0015, -0.0005, 0, 0.0005, 0.0015]:
                if dx == 0 and dy == 0:
                    continue

                new_x = old_x + dx
                new_y = old_y + dy

                if new_x < 1e-7 or new_x > 1.0 - 1e-7:
                    continue
                if new_y < 1e-7 or new_y > 1.0 - 1e-7:
                    continue

                new_r = get_max_radius(new_x, new_y, other_circles)

                if new_r > best_config[2] + 1e-13:
                    best_config = [new_x, new_y, new_r]

        circles[i] = best_config

# Phase 7: Final validation and safe clamping with strict boundaries
for circle in circles:
    circle[0] = max(circle[2] + 1e-11, min(1.0 - circle[2] - 1e-11, circle[0]))
    circle[1] = max(circle[2] + 1e-11, min(1.0 - circle[2] - 1e-11, circle[1]))

    other = [c for c in circles if c is not circle]
    circle[2] = min(circle[2], get_max_radius(circle[0], circle[1], other))

# Final repair: if any circle is invalid, shrink it
for circle in circles:
    x, y, r = circle
    while r > 0 and (x - r < 0 or x + r > 1.0 or y - r < 0 or y + r > 1.0):
        r *= 0.99

    for other in circles:
        if other is circle:
            continue
        cx, cy, cr = other
        d = distance((x, y), (cx, cy))
        if d < r + cr:
            r = max(0, d - cr)

    circle[2] = r

print(circles)
