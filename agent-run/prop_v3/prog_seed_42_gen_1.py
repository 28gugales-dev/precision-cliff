import math
import random

def solve():
    random.seed(42)
    n = 26

    # Hexagonal close-packed grid initialization with optimized row configuration
    positions = []
    row_configs = [(5, 0.0), (6, 0.5/6), (5, 0.0), (6, 0.5/6), (4, 0.0)]

    y_step = 1.0 / 5.0
    circle_idx = 0

    for row_num, (cols, x_offset) in enumerate(row_configs):
        y = (row_num + 0.5) * y_step
        for col_num in range(cols):
            if circle_idx >= n:
                break
            x = (col_num + 0.5 + x_offset * cols) / cols if row_num % 2 == 1 else (col_num + 0.5) / cols
            positions.append([x, y])
            circle_idx += 1

    # Normalize coordinates to [0,1] with minimal margin
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Reduced margin for larger circles
    margin = 0.003
    if max_x > min_x:
        scale_x = (1.0 - 2 * margin) / (max_x - min_x)
        positions = [[(p[0] - min_x) * scale_x + margin, p[1]] for p in positions]

    if max_y > min_y:
        scale_y = (1.0 - 2 * margin) / (max_y - min_y)
        positions = [[p[0], (p[1] - min_y) * scale_y + margin] for p in positions]

    # Initialize radii with larger starting value
    radii = [0.005] * n

    # Multi-phase optimization: grow-relax-grow cycle
    for phase in range(3):
        # Radius growth phase
        max_iterations = 1000
        convergence_threshold = 1e-12

        for iteration in range(max_iterations):
            max_change = 0.0

            for i in range(n):
                x, y = positions[i]

                # Maximum radius limited by boundaries
                max_r = min(x, y, 1.0 - x, 1.0 - y)

                # Maximum radius limited by other circles
                for j in range(n):
                    if i != j:
                        xj, yj = positions[j]
                        rj = radii[j]
                        dist = math.sqrt((x - xj) ** 2 + (y - yj) ** 2)
                        max_r = min(max_r, dist - rj - 1e-11)

                # Only grow, never shrink
                if max_r > radii[i]:
                    change = max_r - radii[i]
                    max_change = max(max_change, change)
                    radii[i] = max_r

            # Stop if convergence achieved
            if max_change < convergence_threshold:
                break

        # Position relaxation phase (except last iteration)
        if phase < 2:
            for i in range(n):
                x, y = positions[i]
                fx, fy = 0.0, 0.0

                # Compute repulsive forces from other circles
                for j in range(n):
                    if i != j:
                        dx = x - positions[j][0]
                        dy = y - positions[j][1]
                        dist_sq = dx * dx + dy * dy
                        dist = math.sqrt(dist_sq) + 1e-10

                        # Target distance (sum of radii with safety margin)
                        target_dist = radii[i] + radii[j] + 0.001

                        # Repulsive force if too close
                        if dist < target_dist:
                            force = (target_dist - dist) / dist
                            fx += dx * force
                            fy += dy * force

                # Apply small positional update
                step = 0.0003
                new_x = x + fx * step
                new_y = y + fy * step

                # Keep within unit square with safety margin
                safety = 0.001
                new_x = max(safety, min(1.0 - safety, new_x))
                new_y = max(safety, min(1.0 - safety, new_y))

                positions[i] = [new_x, new_y]

    # Final validation and safety pass
    result = []
    for i in range(n):
        x, y = positions[i]
        r = radii[i]

        # Final clamp to ensure validity
        r = min(r, x, y, 1.0 - x, 1.0 - y)
        r = max(r, 0.0)

        # Additional safety check
        if x - r < -1e-9 or x + r > 1.0 + 1e-9 or y - r < -1e-9 or y + r > 1.0 + 1e-9:
            r = min(r, x, y, 1.0 - x, 1.0 - y)

        result.append([x, y, r])

    return result

circles = solve()
print(circles)
