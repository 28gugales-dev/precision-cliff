import math
import random
import itertools
import functools

random.seed(1111)

def dist(c1, c2):
    """Euclidean distance between circle centers."""
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

def in_bounds(x, y, r):
    """Check if circle is strictly inside [0,1]x[0,1]."""
    return x - r >= -1e-10 and x + r <= 1 + 1e-10 and y - r >= -1e-10 and y + r <= 1 + 1e-10

def get_max_radius(x, y, circles, idx):
    """Get maximum radius for a circle at (x,y) given other circles."""
    r_max = min(x, 1 - x, y, 1 - y)
    for j in range(len(circles)):
        if j != idx:
            d = dist([x, y, 0], circles[j])
            r_max = min(r_max, d - circles[j][2])
    return max(0, r_max)

# ==============================================================================
# STEP 1: Create initial placement with multiple strategies, pick best
# ==============================================================================

best_circles = None
best_score = -1

for strategy in range(2):
    circles = []

    if strategy == 0:
        # Hexagonal packing (proven good in previous gen)
        n_cols = 6
        hex_spacing_x = 1.0 / (n_cols - 1)
        hex_spacing_y = hex_spacing_x * math.sqrt(3) / 2

        row = 0
        while len(circles) < 26:
            y = row * hex_spacing_y
            if y > 1.0 + 1e-9:
                break
            x_offset = hex_spacing_x / 2 if row % 2 == 1 else 0
            col = 0
            while len(circles) < 26:
                x = col * hex_spacing_x + x_offset
                if x > 1.0 + 1e-9:
                    break
                x = min(x, 1.0)
                y = min(y, 1.0)
                circles.append([x, y, 0.01])
                col += 1
            row += 1
        circles = circles[:26]

    elif strategy == 1:
        # Grid-based placement with perturbation
        grid_size = 6
        spacing = 1.0 / (grid_size - 1) if grid_size > 1 else 0.5
        for i in range(26):
            row = i // grid_size
            col = i % grid_size
            x = col * spacing + random.uniform(-0.02, 0.02)
            y = row * spacing + random.uniform(-0.02, 0.02)
            x = max(0.01, min(0.99, x))
            y = max(0.01, min(0.99, y))
            circles.append([x, y, 0.01])

    # ==============================================================================
    # STEP 2: Aggressive radius growth phase
    # ==============================================================================
    for iteration in range(3000):
        old_radii = [c[2] for c in circles]

        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            circles[i][2] = max(0, min(max_r, circles[i][2] + 0.0015))

        new_radii = [c[2] for c in circles]
        max_delta = max(abs(new_radii[i] - old_radii[i]) for i in range(26)) if new_radii else 0

        if max_delta < 1e-12:
            break

    # ==============================================================================
    # STEP 3: Maximize each radius exactly
    # ==============================================================================
    for _ in range(250):
        changed = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed = True
        if not changed:
            break

    # ==============================================================================
    # STEP 4: Multi-scale aggressive position adjustment
    # ==============================================================================
    step_sizes = [0.010, 0.006, 0.003, 0.0015]

    for step_size in step_sizes:
        for shift_iter in range(200):
            shifted = False
            for i in range(26):
                x, y, r = circles[i]
                best_r = r
                best_x, best_y = x, y

                for dx in [-step_size, -step_size/2, 0, step_size/2, step_size]:
                    for dy in [-step_size, -step_size/2, 0, step_size/2, step_size]:
                        if dx == 0 and dy == 0:
                            continue

                        nx = x + dx
                        ny = y + dy

                        if 0 <= nx <= 1 and 0 <= ny <= 1:
                            nr = get_max_radius(nx, ny, circles, i)
                            if nr > best_r + 1e-12:
                                best_r = nr
                                best_x = nx
                                best_y = ny
                                shifted = True

                circles[i] = [best_x, best_y, best_r]

            if not shifted:
                break

    # ==============================================================================
    # STEP 5: Radius maximization after position adjustments
    # ==============================================================================
    for _ in range(500):
        changed = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed = True
        if not changed:
            break

    # ==============================================================================
    # STEP 6: Ultra-fine position refinement (smallest circles prioritized)
    # ==============================================================================
    circle_indices_by_radius = sorted(range(26), key=lambda i: circles[i][2])

    for priority_pass in range(3):
        for shift_iter in range(100):
            shifted = False
            for idx in circle_indices_by_radius:
                x, y, r = circles[idx]
                best_r = r
                best_x, best_y = x, y

                for dx in [-0.002, -0.001, 0, 0.001, 0.002]:
                    for dy in [-0.002, -0.001, 0, 0.001, 0.002]:
                        if dx == 0 and dy == 0:
                            continue

                        nx = x + dx
                        ny = y + dy

                        if 0 <= nx <= 1 and 0 <= ny <= 1:
                            nr = get_max_radius(nx, ny, circles, idx)
                            if nr > best_r + 1e-12:
                                best_r = nr
                                best_x = nx
                                best_y = ny
                                shifted = True

                circles[idx] = [best_x, best_y, best_r]

            if not shifted:
                break

    # ==============================================================================
    # STEP 7: Final radius maximization
    # ==============================================================================
    for _ in range(300):
        changed = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed = True
        if not changed:
            break

    # ==============================================================================
    # STEP 8: Validation and cleanup
    # ==============================================================================
    for i in range(26):
        x, y, r = circles[i]
        r = min(r, x, 1 - x, y, 1 - y)
        circles[i][2] = max(0, r)
        circles[i][0] = max(0, min(1, x))
        circles[i][1] = max(0, min(1, y))

    # Compute score for this strategy
    score = sum(c[2] for c in circles)

    if score > best_score:
        best_score = score
        best_circles = [c[:] for c in circles]

# ==============================================================================
# STEP 9: Additional optimization on best solution
# ==============================================================================
circles = best_circles

# Final aggressive fine-tuning
for fine_iter in range(100):
    changed = False
    for i in range(26):
        x, y, r = circles[i]
        best_r = r
        best_x, best_y = x, y

        for dx in [-0.0008, -0.0004, 0, 0.0004, 0.0008]:
            for dy in [-0.0008, -0.0004, 0, 0.0004, 0.0008]:
                if dx == 0 and dy == 0:
                    continue

                nx = x + dx
                ny = y + dy

                if 0 <= nx <= 1 and 0 <= ny <= 1:
                    nr = get_max_radius(nx, ny, circles, i)
                    if nr > best_r + 1e-12:
                        best_r = nr
                        best_x = nx
                        best_y = ny
                        changed = True

        circles[i] = [best_x, best_y, best_r]

    # Radius maximization after fine position adjustment
    for _ in range(50):
        changed_r = False
        for i in range(26):
            max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
            if max_r > circles[i][2] + 1e-12:
                circles[i][2] = max_r
                changed_r = True
        if not changed_r:
            break

    if not changed:
        break

# ==============================================================================
# STEP 10: Final validation
# ==============================================================================
for i in range(26):
    x, y, r = circles[i]
    r = min(r, x, 1 - x, y, 1 - y)
    circles[i][2] = max(0, r)
    circles[i][0] = max(0, min(1, x))
    circles[i][1] = max(0, min(1, y))
    assert in_bounds(circles[i][0], circles[i][1], circles[i][2]), f"Circle {i} out of bounds"
    for j in range(i + 1, 26):
        d = dist(circles[i], circles[j])
        assert d >= circles[i][2] + circles[j][2] - 1e-9, f"Circles {i} and {j} overlap"

print(circles)
