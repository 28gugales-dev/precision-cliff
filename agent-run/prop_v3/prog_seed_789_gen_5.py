import math
import random

def pack_circles():
    """Pack 26 circles in unit square, maximizing sum of radii."""
    random.seed(789)

    circles = []

    # Phase 1: Greedy placement - place each circle to maximize its radius
    for circle_idx in range(26):
        best_circle = None
        best_r = 0

        candidates = []

        # Grid-based candidates (cover regular positions)
        for i in range(7):
            for j in range(6):
                x = 0.07 + i * (0.86 / 6.0)
                y = 0.08 + j * (0.84 / 5.0)
                if 0.01 <= x <= 0.99 and 0.01 <= y <= 0.99:
                    candidates.append((x, y))

        # Random candidates for exploration
        for _ in range(300):
            x = random.uniform(0.01, 0.99)
            y = random.uniform(0.01, 0.99)
            candidates.append((x, y))

        # Evaluate each candidate position
        for x, y in candidates:
            r_max = compute_max_radius(x, y, circles)
            if r_max > best_r and r_max > 1e-8:
                best_r = r_max
                best_circle = [x, y, r_max]

        if best_circle:
            circles.append(best_circle)

    # Phase 2: Single-pass position refinement (no while loops to avoid timeout)
    for idx in range(len(circles)):
        x, y, r = circles[idx]

        best_x, best_y, best_r = x, y, r

        # Try nearby positions with limited search
        for dx in [-0.003, -0.001, 0.001, 0.003]:
            for dy in [-0.003, -0.001, 0.001, 0.003]:
                nx = x + dx
                ny = y + dy
                if 0.001 <= nx <= 0.999 and 0.001 <= ny <= 0.999:
                    nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                    if nr > best_r + 1e-10:
                        best_x, best_y, best_r = nx, ny, nr

        if best_x != x or best_y != y:
            circles[idx] = [best_x, best_y, best_r * 0.995]
        else:
            circles[idx][2] = best_r * 0.995

    # Phase 3: Iterative radius optimization (limited passes)
    for pass_num in range(3):
        for idx in range(len(circles)):
            x, y = circles[idx][:2]
            r_new = compute_max_radius(x, y, circles, skip_idx=idx) * 0.995
            if r_new > circles[idx][2]:
                circles[idx][2] = r_new

    # Phase 4: Final aggressive radius push
    for idx in range(len(circles)):
        x, y = circles[idx][:2]
        circles[idx][2] = compute_max_radius(x, y, circles, skip_idx=idx) * 0.998

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
        r_max = min(r_max, dist - cr)

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
    # Fallback: shrink all radii by 5% to ensure validity
    for circle in result:
        circle[2] *= 0.95

print(result)
