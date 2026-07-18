import math
import random
import itertools

def pack_circles():
    """Pack 26 circles in unit square, maximizing sum of radii."""
    random.seed(789)

    circles = []

    # Phase 1: Smarter initial placement using hexagonal-inspired grid
    # Generate candidates with better coverage
    candidates_initial = []

    # Hexagonal-like pattern for efficient packing
    hex_rows = 6
    hex_cols = 5
    row_height = 1.0 / (hex_rows + 1)
    col_width = 1.0 / (hex_cols + 1)

    for i in range(hex_cols):
        for j in range(hex_rows):
            x = (i + 1) * col_width
            if j % 2 == 1:
                x += col_width * 0.5
            y = (j + 1) * row_height
            if 0.01 <= x <= 0.99:
                candidates_initial.append((x, y))

    # Add random candidates for diversity
    for _ in range(250):
        x = random.uniform(0.02, 0.98)
        y = random.uniform(0.02, 0.98)
        candidates_initial.append((x, y))

    # Place 26 circles greedily
    for circle_idx in range(26):
        best_circle = None
        best_r = 0
        best_pos = None

        for x, y in candidates_initial:
            r_max = compute_max_radius(x, y, circles)
            if r_max > best_r and r_max > 1e-9:
                best_r = r_max
                best_circle = [x, y, r_max]
                best_pos = (x, y)

        if best_circle:
            circles.append(best_circle)
            # Remove used candidate and nearby ones
            if best_pos:
                candidates_initial = [
                    (cx, cy) for cx, cy in candidates_initial
                    if math.sqrt((cx - best_pos[0])**2 + (cy - best_pos[1])**2) > 0.08
                ]

    # Phase 2: Aggressive radius growth - multiple expansion passes
    for growth_iteration in range(8):
        for idx in range(len(circles)):
            x, y, r = circles[idx]
            new_r = compute_max_radius(x, y, circles, skip_idx=idx)
            if new_r > r:
                circles[idx][2] = new_r * 0.99

    # Phase 3: Position refinement with finer steps
    for opt_round in range(3):
        for idx in range(len(circles)):
            x, y, r = circles[idx]
            improved = True
            step_size = 0.004

            while improved:
                improved = False
                best_score = sum(c[2] for c in circles)
                best_new_pos = (x, y)

                # Try 8 directions
                for dx, dy in [(-step_size, 0), (step_size, 0),
                               (0, -step_size), (0, step_size),
                               (-step_size, -step_size), (-step_size, step_size),
                               (step_size, -step_size), (step_size, step_size)]:
                    nx = x + dx
                    ny = y + dy

                    if 0.002 <= nx <= 0.998 and 0.002 <= ny <= 0.998:
                        nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                        if nr > 1e-9:
                            circles[idx] = [nx, ny, nr * 0.98]
                            new_score = sum(c[2] for c in circles)

                            if new_score > best_score + 1e-10:
                                best_score = new_score
                                best_new_pos = (nx, ny)
                                x, y = nx, ny
                                improved = True
                            else:
                                circles[idx] = [x, y, r]

                if not improved:
                    break

    # Phase 4: Final aggressive radius optimization
    # Try to maximize radii with tight constraints
    for final_iteration in range(5):
        total_score_before = sum(c[2] for c in circles)

        for idx in range(len(circles)):
            x, y = circles[idx][:2]
            r_candidate = compute_max_radius(x, y, circles, skip_idx=idx)
            if r_candidate > circles[idx][2]:
                circles[idx][2] = min(r_candidate, circles[idx][2] * 1.02)

        total_score_after = sum(c[2] for c in circles)
        if total_score_after < total_score_before + 1e-8:
            break

    # Phase 5: Micro-adjustments - fine-tune to squeeze extra radius
    for micro_iter in range(4):
        for idx in range(len(circles)):
            x, y, r = circles[idx]

            # Try tiny movements
            for tiny_dx in [-0.0005, 0.0005]:
                for tiny_dy in [-0.0005, 0.0005]:
                    nx = x + tiny_dx
                    ny = y + tiny_dy

                    if 0.001 <= nx <= 0.999 and 0.001 <= ny <= 0.999:
                        nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                        if nr > r:
                            circles[idx] = [nx, ny, nr * 0.999]
                            break

    return circles

def compute_max_radius(x, y, circles, skip_idx=-1):
    """Compute the maximum radius for a circle at (x, y) without overlaps."""
    # Boundary constraints
    r_max = min(x, y, 1.0 - x, 1.0 - y)

    # Collision constraints with existing circles
    for i, (cx, cy, cr) in enumerate(circles):
        if i == skip_idx:
            continue
        dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        if dist > 0:
            r_max = min(r_max, dist - cr)
        else:
            # Same position (shouldn't happen, but safety check)
            r_max = -1.0

    return max(0.0, r_max)

def validate_geometry(circles):
    """Validate that the packing is geometrically valid."""
    if len(circles) != 26:
        return False

    # Check boundary constraints
    for x, y, r in circles:
        if r < -1e-10 or x - r < -1e-9 or x + r > 1.0 + 1e-9:
            return False
        if y - r < -1e-10 or y + r > 1.0 + 1e-9:
            return False

    # Check non-overlap constraints
    for i, (x1, y1, r1) in enumerate(circles):
        for x2, y2, r2 in circles[i + 1:]:
            dist = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
            if dist < r1 + r2 - 1e-8:
                return False

    return True

# Generate and validate the packing
result = pack_circles()

# Ensure validity before outputting
if not validate_geometry(result):
    # Shrink radii to ensure validity
    for circle in result:
        circle[2] *= 0.93

print(result)
