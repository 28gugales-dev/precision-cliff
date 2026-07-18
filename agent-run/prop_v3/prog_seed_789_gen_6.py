import math
import random

def pack_circles():
    """Pack 26 circles in unit square, maximizing sum of radii."""
    random.seed(789)

    circles = []

    # Phase 1: Smart initial placement using optimized grid/hexagonal approach
    # Try to place circles in a structured pattern first
    grid_positions = []

    # Hexagonal-like grid for better space efficiency
    rows = 6
    cols = 5
    row_height = 1.0 / (rows + 1)
    col_width = 1.0 / (cols + 1)

    for i in range(rows):
        for j in range(cols):
            x = (j + 1) * col_width
            if i % 2 == 1:  # Offset odd rows
                x += col_width / 2.0
            y = (i + 1) * row_height
            if x <= 1.0 and y <= 1.0:
                grid_positions.append((x, y))

    # Add additional random positions for remaining slots
    extra_positions = []
    for _ in range(100):
        x = random.uniform(0.05, 0.95)
        y = random.uniform(0.05, 0.95)
        extra_positions.append((x, y))

    all_candidates = grid_positions + extra_positions

    # Greedy placement
    for circle_idx in range(26):
        best_circle = None
        best_r = 0
        best_pos_idx = -1

        for pos_idx, (x, y) in enumerate(all_candidates):
            if any(abs(x - c[0]) < 1e-6 and abs(y - c[1]) < 1e-6 for c in circles):
                continue

            r_max = compute_max_radius(x, y, circles)
            if r_max > best_r and r_max > 1e-8:
                best_r = r_max
                best_circle = [x, y, r_max]
                best_pos_idx = pos_idx

        if best_circle:
            circles.append(best_circle)
            if best_pos_idx >= 0:
                all_candidates.pop(best_pos_idx)

    # Phase 2: Aggressive radius growth
    for growth_pass in range(15):
        improved = False
        for idx in range(len(circles)):
            x, y, r = circles[idx]
            new_r = compute_max_radius(x, y, circles, skip_idx=idx)
            if new_r > r + 1e-9:
                circles[idx][2] = new_r * 0.998
                improved = True
        if not improved:
            break

    # Phase 3: Position optimization with multiple scales
    for scale_pass in range(3):
        step_size = 0.02 / (scale_pass + 1)
        steps = [-step_size, 0, step_size]

        for opt_round in range(8):
            improved = False
            for idx in range(len(circles)):
                x, y, r = circles[idx]
                current_score = sum(c[2] for c in circles)

                best_score = current_score
                best_x, best_y = x, y

                for dx in steps:
                    for dy in steps:
                        if dx == 0 and dy == 0:
                            continue
                        nx = x + dx
                        ny = y + dy
                        if 0.001 <= nx <= 0.999 and 0.001 <= ny <= 0.999:
                            nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                            if nr > 1e-8:
                                circles[idx] = [nx, ny, nr * 0.998]
                                new_score = sum(c[2] for c in circles)
                                if new_score > best_score + 1e-10:
                                    best_score = new_score
                                    best_x, best_y = nx, ny
                                    improved = True
                                else:
                                    circles[idx] = [x, y, r]

                if improved:
                    x, y = best_x, best_y
                    circles[idx] = [x, y, compute_max_radius(x, y, circles, skip_idx=idx) * 0.998]

            if not improved:
                break

    # Phase 4: Fine-grained radius optimization
    for _ in range(10):
        for idx in range(len(circles)):
            x, y = circles[idx][:2]
            circles[idx][2] = compute_max_radius(x, y, circles, skip_idx=idx) * 0.997

    # Phase 5: Micro-refinement with tiny steps
    for micro_pass in range(5):
        for idx in range(len(circles)):
            x, y, r = circles[idx]
            current_score = sum(c[2] for c in circles)

            improved = True
            while improved:
                improved = False
                micro_steps = [-0.0005, -0.0002, 0.0002, 0.0005]

                for dx in micro_steps:
                    for dy in micro_steps:
                        nx = x + dx
                        ny = y + dy
                        if 0.0001 <= nx <= 0.9999 and 0.0001 <= ny <= 0.9999:
                            nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                            if nr > 1e-8:
                                circles[idx] = [nx, ny, nr * 0.996]
                                new_score = sum(c[2] for c in circles)
                                if new_score > current_score + 1e-11:
                                    current_score = new_score
                                    x, y = nx, ny
                                    improved = True
                                    break
                                else:
                                    circles[idx] = [x, y, r]
                    if improved:
                        break

    # Final radius pass
    for idx in range(len(circles)):
        x, y = circles[idx][:2]
        circles[idx][2] = compute_max_radius(x, y, circles, skip_idx=idx) * 0.996

    return circles


def compute_max_radius(x, y, circles, skip_idx=-1):
    """Compute the maximum radius for a circle at (x, y) without overlaps."""
    # Constraint from box boundaries
    r_max = min(x, y, 1.0 - x, 1.0 - y)

    # Constraint from existing circles
    for i, (cx, cy, cr) in enumerate(circles):
        if i == skip_idx:
            continue
        dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        # New circle can have radius at most dist - cr (to avoid overlap)
        r_max = min(r_max, max(0.0, dist - cr))

    return max(0.0, r_max)


def validate_geometry(circles):
    """Validate that the packing is geometrically valid."""
    if len(circles) != 26:
        return False

    # Check boundary constraints
    for x, y, r in circles:
        if r < 0 or x - r < -1e-9 or x + r > 1.0 + 1e-9:
            return False
        if y - r < -1e-9 or y + r > 1.0 + 1e-9:
            return False

    # Check non-overlap constraints
    for i, (x1, y1, r1) in enumerate(circles):
        for x2, y2, r2 in circles[i + 1:]:
            dist = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
            if dist < r1 + r2 - 1e-9:
                return False

    return True


# Generate and validate the packing
result = pack_circles()

# Ensure validity before outputting
if not validate_geometry(result):
    # Shrink all radii to ensure validity
    for circle in result:
        circle[2] *= 0.94

print(result)
