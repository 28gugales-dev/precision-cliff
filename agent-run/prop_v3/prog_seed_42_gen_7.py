import math
import random

def solve():
    random.seed(42)
    n = 26

    def compute_max_radius(x, y, positions, radii, skip_idx=-1):
        """Compute maximum radius for circle at (x, y)."""
        max_r = min(x, y, 1.0 - x, 1.0 - y)
        for j in range(len(positions)):
            if j == skip_idx:
                continue
            ox, oy = positions[j]
            or_val = radii[j]
            dist = math.sqrt((x - ox) ** 2 + (y - oy) ** 2)
            max_r = min(max_r, dist - or_val - 1e-12)
        return max(0, max_r)

    def grow_radii_refined(positions, max_iterations=3000, threshold=1e-12):
        """Iteratively grow radii with stricter convergence."""
        radii = [0.001] * len(positions)

        for iteration in range(max_iterations):
            max_change = 0.0

            for i in range(len(positions)):
                x, y = positions[i]
                new_r = compute_max_radius(x, y, positions, radii, skip_idx=i)
                change = new_r - radii[i]

                if change > threshold:
                    radii[i] = new_r
                    max_change = max(max_change, change)

            if max_change < threshold:
                break

        return radii

    def local_search_positions(positions, radii, num_probes=3):
        """Local search to improve positions slightly."""
        best_score = sum(radii)
        best_positions = [list(p) for p in positions]
        improved = True

        while improved and num_probes > 0:
            improved = False
            step = 0.003

            for i in range(len(positions)):
                for dx, dy in [(-step, 0), (step, 0), (0, -step), (0, step)]:
                    test_pos = [list(p) for p in best_positions]
                    test_pos[i][0] = max(0.001, min(0.999, test_pos[i][0] + dx))
                    test_pos[i][1] = max(0.001, min(0.999, test_pos[i][1] + dy))

                    test_radii = grow_radii_refined(test_pos, max_iterations=500)
                    test_score = sum(test_radii)

                    if test_score > best_score + 1e-11:
                        best_score = test_score
                        best_positions = test_pos
                        best_radii = test_radii
                        improved = True
                        break

                if improved:
                    break

            num_probes -= 1

        return best_positions, best_radii

    best_circles = None
    best_score = -1.0

    # Expanded set of configurations to try
    configurations = [
        # Original champion variants
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 4.0),
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 3.5),
        ([(5, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (4, 0.0)], 3.8),

        # Alternative hexagonal arrangements
        ([(6, 0.0), (5, 1/8), (6, 0.0), (5, 1/8), (4, 0.0)], 4.0),
        ([(6, 0.0), (5, 1/8), (6, 0.0), (5, 1/8), (3, 0.0)], 4.0),
        ([(5, 0.0), (6, 0.06), (5, 0.0), (6, 0.06), (4, 0.0)], 3.9),
        ([(5, 0.0), (6, 0.07), (5, 0.0), (6, 0.07), (4, 0.0)], 3.7),

        # Rectangular grids
        ([(5, 0.0), (5, 0.0), (5, 0.0), (5, 0.0), (6, 0.0)], 4.0),
        ([(6, 0.0), (6, 0.0), (6, 0.0), (6, 0.0), (2, 0.0)], 4.0),
        ([(5, 0.0), (5, 0.0), (5, 0.0), (5, 0.0), (5, 0.0), (1, 0.0)], 5.0),

        # Alternative patterns
        ([(4, 0.0), (6, 1/8), (6, 0.0), (6, 1/8), (4, 0.0)], 4.0),
        ([(6, 0.0), (6, 1/8), (5, 0.0), (6, 1/8), (3, 0.0)], 4.0),
        ([(5, 0.0), (6, 0.05), (5, 0.0), (6, 0.05), (4, 0.0)], 3.75),
        ([(5, 0.0), (6, 0.09), (5, 0.0), (6, 0.09), (4, 0.0)], 4.1),

        # Denser arrangements
        ([(7, 0.0), (6, 1/8), (6, 0.0), (5, 1/8), (2, 0.0)], 4.0),
        ([(6, 0.0), (6, 1/8), (6, 0.0), (6, 1/8), (2, 0.0)], 4.0),
    ]

    for idx, (row_configs, y_step_divisor) in enumerate(configurations):
        positions = []
        circle_idx = 0

        for row_num, (cols, x_offset) in enumerate(row_configs):
            y = row_num / y_step_divisor
            for col_num in range(cols):
                if circle_idx >= n:
                    break
                x = x_offset + (col_num + 0.5) / cols
                positions.append([x, y])
                circle_idx += 1

        if circle_idx < n:
            continue

        # Normalize coordinates
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        margin = 0.012
        if max_x > min_x:
            scale_x = (1.0 - 2.0 * margin) / (max_x - min_x)
            positions = [[(p[0] - min_x) * scale_x + margin, p[1]] for p in positions]

        if max_y > min_y:
            scale_y = (1.0 - 2.0 * margin) / (max_y - min_y)
            positions = [[p[0], (p[1] - min_y) * scale_y + margin] for p in positions]

        # Grow radii with strict convergence
        radii = grow_radii_refined(positions, max_iterations=3000, threshold=1e-12)

        # Local search on first few configurations
        if idx < 4:
            positions, radii = local_search_positions(positions, radii, num_probes=2)

        # Final safety checks and clamp
        result = []
        for i in range(n):
            x, y, r = positions[i][0], positions[i][1], radii[i]
            r = min(r, x, y, 1.0 - x, 1.0 - y)

            if x - r < -1e-9 or x + r > 1.0 + 1e-9 or y - r < -1e-9 or y + r > 1.0 + 1e-9:
                r = min(r, x, y, 1.0 - x, 1.0 - y)

            result.append([x, y, r])

        score = sum(c[2] for c in result)
        if score > best_score:
            best_score = score
            best_circles = result

    return best_circles if best_circles else [[0.5, 0.5, 0.001] for _ in range(n)]

circles = solve()
print(circles)
