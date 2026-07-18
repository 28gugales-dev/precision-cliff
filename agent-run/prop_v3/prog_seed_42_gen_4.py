import math
import random

def solve():
    random.seed(42)
    n = 26

    def evaluate_configuration(positions, max_iterations=1500, refine_step_size=0.0):
        """Grow radii given positions, optionally with position refinement."""
        radii = [0.001] * n
        positions_work = [list(p) for p in positions]

        for iteration in range(max_iterations):
            max_change = 0.0

            for i in range(n):
                x, y = positions_work[i]

                # Maximum radius limited by boundaries
                max_r = min(x, y, 1.0 - x, 1.0 - y)

                # Maximum radius limited by other circles
                for j in range(n):
                    if i != j:
                        xj, yj = positions_work[j]
                        rj = radii[j]
                        dist = math.sqrt((x - xj) ** 2 + (y - yj) ** 2)
                        max_r = min(max_r, dist - rj - 1e-12)

                if max_r > radii[i]:
                    change = max_r - radii[i]
                    max_change = max(max_change, change)
                    radii[i] = max_r

            # Position refinement phase (light perturbation)
            if refine_step_size > 0 and iteration % 50 == 0 and iteration > 0:
                for i in range(n):
                    dx = (random.random() - 0.5) * refine_step_size
                    dy = (random.random() - 0.5) * refine_step_size
                    new_x = positions_work[i][0] + dx
                    new_y = positions_work[i][1] + dy

                    # Clamp to valid range
                    new_x = max(radii[i], min(1.0 - radii[i], new_x))
                    new_y = max(radii[i], min(1.0 - radii[i], new_y))

                    positions_work[i] = [new_x, new_y]

            if max_change < 1e-10:
                break

        return positions_work, radii, sum(radii)

    def grid_config_to_positions(row_configs, y_step_divisor):
        """Convert row configuration to positions with normalization."""
        positions = []
        circle_idx = 0

        for row_num, (cols, x_offset) in enumerate(row_configs):
            y = row_num / y_step_divisor
            for col_num in range(cols):
                if circle_idx >= n:
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

        return positions

    best_circles = None
    best_score = -1.0

    # Extended set of grid configurations
    configurations = [
        # Hexagonal patterns (champion variants)
        ([(5, 0.0), (6, 0.125), (5, 0.0), (6, 0.125), (4, 0.0)], 4.0),
        ([(5, 0.0), (6, 0.125), (5, 0.0), (6, 0.125), (4, 0.0)], 3.8),
        ([(5, 0.0), (6, 0.125), (5, 0.0), (6, 0.125), (4, 0.0)], 4.2),

        # Flipped hexagonal
        ([(6, 0.0), (5, 0.125), (6, 0.0), (5, 0.125), (4, 0.0)], 4.0),
        ([(6, 0.0), (5, 0.125), (6, 0.0), (5, 0.125), (4, 0.0)], 3.8),

        # Different offset values
        ([(5, 0.0), (6, 0.1), (5, 0.0), (6, 0.1), (4, 0.0)], 4.0),
        ([(5, 0.0), (6, 0.15), (5, 0.0), (6, 0.15), (4, 0.0)], 4.0),
        ([(5, 0.0), (6, 0.05), (5, 0.0), (6, 0.05), (4, 0.0)], 4.0),

        # Regular grids
        ([(5, 0.0), (5, 0.0), (5, 0.0), (5, 0.0), (6, 0.0)], 4.0),
        ([(5, 0.0), (5, 0.0), (5, 0.0), (5, 0.0), (6, 0.0)], 4.2),
        ([(6, 0.0), (6, 0.0), (6, 0.0), (6, 0.0), (2, 0.0)], 4.0),

        # Mixed patterns
        ([(4, 0.0), (5, 0.1), (6, 0.0), (5, 0.1), (6, 0.0)], 4.0),
        ([(6, 0.0), (5, 0.1), (6, 0.0), (5, 0.1), (4, 0.0)], 4.0),
        ([(7, 0.0), (5, 0.1), (5, 0.0), (5, 0.1), (3, 0.0)], 4.0),
        ([(4, 0.0), (5, 0.0), (6, 0.0), (5, 0.0), (6, 0.0)], 4.0),

        # Asymmetric patterns
        ([(5, 0.0), (5, 0.1), (5, 0.0), (5, 0.1), (6, 0.0)], 4.0),
        ([(4, 0.0), (6, 0.125), (5, 0.0), (6, 0.125), (5, 0.0)], 4.0),

        # More varied y-step values
        ([(5, 0.0), (6, 0.125), (5, 0.0), (6, 0.125), (4, 0.0)], 3.6),
        ([(5, 0.0), (6, 0.125), (5, 0.0), (6, 0.125), (4, 0.0)], 4.4),
        ([(6, 0.0), (5, 0.125), (6, 0.0), (5, 0.125), (4, 0.0)], 3.8),
        ([(6, 0.0), (5, 0.125), (6, 0.0), (5, 0.125), (4, 0.0)], 4.2),
    ]

    # Primary refinement: try all configurations
    for row_configs, y_step_divisor in configurations:
        positions = grid_config_to_positions(row_configs, y_step_divisor)
        _, radii, score = evaluate_configuration(positions, max_iterations=1500, refine_step_size=0.0)

        if score > best_score:
            best_score = score
            best_circles = [(positions[i][0], positions[i][1], radii[i]) for i in range(n)]

    # Secondary refinement: position perturbation on best configuration
    if best_circles is not None:
        best_pos = [[x, y] for x, y, r in best_circles]
        _, radii_refined, score_refined = evaluate_configuration(best_pos, max_iterations=1000, refine_step_size=0.02)

        if score_refined > best_score:
            best_score = score_refined
            best_circles = [(best_pos[i][0], best_pos[i][1], radii_refined[i]) for i in range(n)]

    # Build final result with safety checks
    result = []
    for i in range(n):
        x, y, r = best_circles[i]

        # Clamp radius to ensure validity
        r = min(r, x, y, 1.0 - x, 1.0 - y)

        # Extra safety: verify no boundary violation
        if x - r < -1e-9 or x + r > 1.0 + 1e-9 or y - r < -1e-9 or y + r > 1.0 + 1e-9:
            r = min(r, x, y, 1.0 - x, 1.0 - y)

        result.append([x, y, r])

    return result

circles = solve()
print(circles)
