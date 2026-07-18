import math
import random

def solve():
    random.seed(42)
    n = 26

    def grow_radii_optimized(positions, max_iterations=2000, convergence_threshold=1e-11):
        """Grow radii with optimized constraints."""
        radii = [0.001] * n

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

            if max_change < convergence_threshold:
                break

        return radii

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
                x = (col_num + 0.5 + x_offset) / cols
                positions.append([x, y])
                circle_idx += 1

        # Normalize coordinates to fit in [0,1]^2 with margin
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        margin = 0.01
        if max_x > min_x:
            scale_x = (1.0 - 2 * margin) / (max_x - min_x)
            positions = [[(p[0] - min_x) * scale_x + margin, p[1]] for p in positions]

        if max_y > min_y:
            scale_y = (1.0 - 2 * margin) / (max_y - min_y)
            positions = [[p[0], (p[1] - min_y) * scale_y + margin] for p in positions]

        # Grow radii
        radii = grow_radii_optimized(positions, max_iterations=2000)

        # Local perturbation refinement: try small position adjustments
        step_size = 0.002
        for _ in range(3):
            improved = False
            for i in range(n):
                x, y = positions[i]
                r = radii[i]

                # Try small perturbations
                for dx, dy in [(step_size, 0), (-step_size, 0), (0, step_size), (0, -step_size)]:
                    new_x, new_y = x + dx, y + dy

                    # Check boundary constraints
                    if new_x - r < -1e-9 or new_x + r > 1.0 + 1e-9:
                        continue
                    if new_y - r < -1e-9 or new_y + r > 1.0 + 1e-9:
                        continue

                    # Check circle overlap
                    valid = True
                    for j in range(n):
                        if i != j:
                            xj, yj = positions[j]
                            rj = radii[j]
                            dist = math.sqrt((new_x - xj) ** 2 + (new_y - yj) ** 2)
                            if dist < r + rj - 1e-9:
                                valid = False
                                break

                    if valid:
                        positions[i] = [new_x, new_y]
                        improved = True
                        break

            if not improved:
                break

        # Final radius re-grow after perturbations
        radii = grow_radii_optimized(positions, max_iterations=1000)

        return positions, radii, sum(radii)

    best_circles = None
    best_score = -1.0

    # Extended set of configurations to try
    configurations = [
        # Original champion hexagonal
        ([(5, 0.0), (6, 0.08), (5, 0.0), (6, 0.08), (4, 0.0)], 4.0),

        # Rectangular grids with different arrangements
        ([(5, 0.0), (5, 0.0), (5, 0.0), (5, 0.0), (6, 0.0)], 4.0),
        ([(6, 0.0), (6, 0.0), (6, 0.0), (6, 0.0), (2, 0.0)], 4.0),
        ([(6, 0.0), (5, 0.0), (6, 0.0), (5, 0.0), (4, 0.0)], 4.0),

        # Hexagonal with different offsets
        ([(5, 0.0), (6, 0.15), (5, 0.0), (6, 0.15), (4, 0.0)], 3.8),
        ([(6, 0.0), (5, 0.12), (6, 0.0), (5, 0.12), (4, 0.0)], 3.8),
        ([(5, 0.0), (6, 0.1), (5, 0.0), (6, 0.1), (4, 0.0)], 3.5),
        ([(6, 0.0), (5, 0.08), (6, 0.0), (5, 0.08), (4, 0.0)], 3.5),

        # More varied patterns
        ([(4, 0.0), (6, 0.1), (5, 0.0), (6, 0.1), (5, 0.0)], 3.8),
        ([(5, 0.0), (5, 0.1), (5, 0.0), (5, 0.1), (6, 0.0)], 4.0),
        ([(6, 0.0), (6, 0.08), (6, 0.0), (6, 0.08), (2, 0.0)], 3.8),
        ([(5, 0.05), (6, 0.1), (5, 0.05), (6, 0.1), (4, 0.0)], 4.0),

        # Different y step sizes with hexagonal patterns
        ([(5, 0.0), (6, 0.12), (5, 0.0), (6, 0.12), (4, 0.0)], 3.6),
        ([(6, 0.0), (5, 0.1), (6, 0.0), (5, 0.1), (4, 0.0)], 3.6),
        ([(5, 0.0), (6, 0.08), (5, 0.0), (6, 0.08), (4, 0.0)], 3.7),
        ([(4, 0.0), (5, 0.08), (4, 0.0), (5, 0.08), (6, 1/6)], 4.0),
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
