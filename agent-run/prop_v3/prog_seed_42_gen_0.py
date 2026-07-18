import math
import random

def solve():
    random.seed(42)
    n = 26

    # Create initial placement using a hexagonal-inspired grid
    # Arrange 26 circles in 5 rows with alternating column counts (5,6,5,6,4)
    positions = []
    row_configs = [(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)]

    y_step = 1.0 / 4.0  # 5 rows need 4 steps
    circle_idx = 0

    for row_num, (cols, x_offset) in enumerate(row_configs):
        y = row_num * y_step
        for col_num in range(cols):
            if circle_idx >= 26:
                break
            x = (col_num + 0.5 + x_offset * cols) / cols
            # Normalize x to stay in [0, 1]
            x = (col_num + 0.5) / cols
            positions.append([x, y])
            circle_idx += 1

    # Normalize coordinates to ensure they fit well in [0,1]^2
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Scale to use most of the unit square while leaving boundary margin
    margin = 0.02
    if max_x > min_x:
        scale_x = (1.0 - 2 * margin) / (max_x - min_x)
        positions = [[(p[0] - min_x) * scale_x + margin, p[1]] for p in positions]

    if max_y > min_y:
        scale_y = (1.0 - 2 * margin) / (max_y - min_y)
        positions = [[p[0], (p[1] - min_y) * scale_y + margin] for p in positions]

    # Initialize radii to small value
    radii = [0.001] * n

    # Iteratively grow radii to maximize coverage
    # Each iteration, for each circle, find the maximum radius that:
    # 1. Keeps it inside [0,1]x[0,1]
    # 2. Doesn't overlap with other circles
    max_iterations = 1000
    convergence_threshold = 1e-10

    for iteration in range(max_iterations):
        max_change = 0.0

        for i in range(n):
            x, y = positions[i]

            # Maximum radius limited by boundaries
            max_r = min(x, y, 1.0 - x, 1.0 - y)

            # Maximum radius limited by other circles
            # For each other circle, we can grow until we touch it
            for j in range(n):
                if i != j:
                    xj, yj = positions[j]
                    rj = radii[j]
                    dist = math.sqrt((x - xj) ** 2 + (y - yj) ** 2)
                    # Allow touching (tangency) but not overlapping
                    # Subtract a tiny epsilon for numerical stability
                    max_r = min(max_r, dist - rj - 1e-12)

            # Only grow, never shrink
            if max_r > radii[i]:
                change = max_r - radii[i]
                max_change = max(max_change, change)
                radii[i] = max_r

        # Stop if convergence achieved
        if max_change < convergence_threshold:
            break

    # Build final result with safety checks
    result = []
    for i in range(n):
        x, y = positions[i]
        r = radii[i]

        # Final clamp to ensure validity
        r = min(r, x, y, 1.0 - x, 1.0 - y)

        # Additional safety: verify no boundary violation
        if x - r < -1e-9 or x + r > 1.0 + 1e-9 or y - r < -1e-9 or y + r > 1.0 + 1e-9:
            r = min(r, x, y, 1.0 - x, 1.0 - y)

        result.append([x, y, r])

    return result

circles = solve()
print(circles)
