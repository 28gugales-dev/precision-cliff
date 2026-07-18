import math
import random
import itertools

def solve():
    random.seed(42)
    n = 26

    def grow_radii(positions, max_iterations=1500):
        """Grow radii to maximize coverage with convergence check."""
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

            if max_change < 1e-11:
                break

        return radii

    def refine_positions(positions, radii, refinement_steps=50):
        """Refine positions via local relaxation."""
        positions = [list(p) for p in positions]

        for step in range(refinement_steps):
            for i in range(n):
                x, y = positions[i]

                # Compute forces from overlapping constraints
                fx, fy = 0.0, 0.0

                for j in range(n):
                    if i != j:
                        xj, yj = positions[j]
                        dist = math.sqrt((x - xj) ** 2 + (y - yj) ** 2)
                        min_dist = radii[i] + radii[j]

                        if dist < min_dist - 1e-9:
                            # Push apart
                            if dist > 1e-9:
                                push = (min_dist - dist) / (2 * dist)
                                fx += push * (x - xj)
                                fy += push * (y - yj)

                # Apply small movement
                move_factor = 0.002
                new_x = x + fx * move_factor
                new_y = y + fy * move_factor

                # Clamp to bounds
                new_x = max(radii[i], min(1.0 - radii[i], new_x))
                new_y = max(radii[i], min(1.0 - radii[i], new_y))

                positions[i] = [new_x, new_y]

        return positions

    def process_configuration(row_configs, y_step_divisor=4.0):
        """Process a row configuration and return score."""
        positions = []
        circle_idx = 0

        # Create grid layout
        for row_num, (cols, x_offset) in enumerate(row_configs):
            y = row_num / y_step_divisor
            for col_num in range(cols):
                if circle_idx >= 26:
                    break
                x = (col_num + x_offset) / cols
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
        radii = grow_radii(positions)

        return positions, radii, sum(radii)

    best_circles = None
    best_score = -1.0

    # Expanded configurations with more variety
    configurations = [
        # Original champion pattern
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 4.0),
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 3.8),
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 3.6),
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 4.2),

        # Regular rectangular grids
        ([(5, 0.0), (5, 0.0), (5, 0.0), (5, 0.0), (6, 0.0)], 4.0),
        ([(6, 0.0), (6, 0.0), (6, 0.0), (6, 0.0), (2, 0.0)], 4.0),
        ([(5, 0.0), (5, 0.0), (5, 0.0), (5, 0.0), (6, 0.0)], 3.8),

        # Flipped hexagonal
        ([(6, 0.0), (5, 0.0), (6, 0.0), (5, 0.0), (4, 0.0)], 4.0),
        ([(6, 0.0), (5, 1/8), (6, 0.0), (5, 1/8), (4, 0.0)], 4.0),

        # Varying offsets
        ([(5, 0.0), (6, 0.05), (5, 0.0), (6, 0.05), (4, 0.0)], 4.0),
        ([(5, 0.0), (6, 0.1), (5, 0.0), (6, 0.1), (4, 0.0)], 4.0),
        ([(5, 0.0), (6, 1/12), (5, 0.0), (6, 1/12), (4, 0.0)], 4.0),

        # Different y-step patterns
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 3.5),
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 3.7),
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 4.5),

        # More uniform distributions
        ([(6, 0.0), (5, 0.0), (5, 0.0), (5, 0.0), (5, 0.0)], 4.0),
        ([(5, 0.0), (5, 0.0), (5, 0.0), (6, 0.0), (5, 0.0)], 4.0),

        # Nested patterns
        ([(4, 0.0), (6, 0.0), (6, 0.0), (6, 0.0), (4, 0.0)], 4.0),
        ([(6, 0.0), (6, 0.0), (5, 0.0), (5, 0.0), (4, 0.0)], 4.0),

        # Additional hexagonal variations
        ([(5, 0.0), (6, 1/10), (5, 0.0), (6, 1/10), (4, 0.0)], 4.0),
        ([(5, 0.0), (6, 3/16), (5, 0.0), (6, 3/16), (4, 0.0)], 4.0),
    ]

    for row_configs, y_step_divisor in configurations:
        positions, radii, score = process_configuration(row_configs, y_step_divisor)

        if score > best_score:
            best_score = score
            best_circles = [(positions[i][0], positions[i][1], radii[i]) for i in range(n)]

    # Try refinement on the best configuration found
    if best_circles is not None:
        best_positions = [[c[0], c[1]] for c in best_circles]
        best_radii = [c[2] for c in best_circles]

        # Refine positions and re-grow radii
        refined_positions = refine_positions(best_positions, best_radii, 80)
        refined_radii = grow_radii(refined_positions)
        refined_score = sum(refined_radii)

        if refined_score > best_score:
            best_score = refined_score
            best_circles = [(refined_positions[i][0], refined_positions[i][1], refined_radii[i]) for i in range(n)]

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
