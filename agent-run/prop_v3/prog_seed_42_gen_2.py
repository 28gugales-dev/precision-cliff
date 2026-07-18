import math
import random

def solve():
    random.seed(42)
    n = 26

    def process_configuration(row_configs, y_step_divisor=4.0):
        """Process a row configuration and return positions, radii, and score."""
        positions = []
        circle_idx = 0

        # Create grid layout
        for row_num, (cols, x_offset) in enumerate(row_configs):
            y = row_num / y_step_divisor
            for col_num in range(cols):
                if circle_idx >= 26:
                    break
                x = (col_num + 0.5) / cols
                positions.append([x, y])
                circle_idx += 1

        # Normalize coordinates to fit in [0,1]^2 with margin
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

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
        max_iterations = 1000
        convergence_threshold = 1e-10

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
                        max_r = min(max_r, dist - rj - 1e-12)

                # Only grow, never shrink
                if max_r > radii[i]:
                    change = max_r - radii[i]
                    max_change = max(max_change, change)
                    radii[i] = max_r

            # Stop if convergence achieved
            if max_change < convergence_threshold:
                break

        return positions, radii, sum(radii)

    best_circles = None
    best_score = -1.0

    # Try multiple grid configurations
    configurations = [
        # Champion's hexagonal arrangement
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 4.0),

        # Alternative 1: regular rectangular grid
        ([(5, 0.0), (5, 0.0), (5, 0.0), (5, 0.0), (6, 0.0)], 4.0),

        # Alternative 2: flipped hexagonal pattern
        ([(6, 0.0), (5, 0.0), (6, 0.0), (5, 0.0), (4, 0.0)], 4.0),

        # Alternative 3: hexagonal with smaller offset
        ([(5, 0.0), (6, 0.05), (5, 0.0), (6, 0.05), (4, 0.0)], 4.0),

        # Alternative 4: more uniform distribution
        ([(6, 0.0), (6, 0.0), (6, 0.0), (6, 0.0), (2, 0.0)], 4.0),

        # Alternative 5: hexagonal with different step
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 3.5),
    ]

    for row_configs, y_step_divisor in configurations:
        positions, radii, score = process_configuration(row_configs, y_step_divisor)

        if score > best_score:
            best_score = score
            best_circles = [(positions[i][0], positions[i][1], radii[i]) for i in range(n)]

    # Build final result with safety checks
    result = []
    for i in range(n):
        x, y, r = best_circles[i]

        # Final clamp to ensure validity
        r = min(r, x, y, 1.0 - x, 1.0 - y)

        # Additional safety: verify no boundary violation
        if x - r < -1e-9 or x + r > 1.0 + 1e-9 or y - r < -1e-9 or y + r > 1.0 + 1e-9:
            r = min(r, x, y, 1.0 - x, 1.0 - y)

        result.append([x, y, r])

    return result

circles = solve()
print(circles)
