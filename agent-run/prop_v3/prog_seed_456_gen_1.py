import random
import math

def get_max_radius(x, y, circles, i):
    """Get maximum radius for circle i at position (x, y) without violating constraints."""
    r_max = min(x, 1.0 - x, y, 1.0 - y)

    for j, (x2, y2, r2) in enumerate(circles):
        if i != j:
            dist = math.sqrt((x - x2) ** 2 + (y - y2) ** 2)
            r_max = min(r_max, max(0.0, dist - r2))

    return max(0.0, r_max)

def optimize_config(circles):
    """Optimize a circle configuration through growth and position refinement."""
    circles = [list(c) for c in circles]

    # Multi-cycle optimization
    for cycle in range(4):
        # Phase 1: Iterative radius growth
        for iteration in range(1000):
            max_growth = 0.0
            for i in range(26):
                x, y, r = circles[i]
                new_r = get_max_radius(x, y, circles, i)
                growth = new_r - r
                max_growth = max(max_growth, growth)
                circles[i][2] = new_r

            if max_growth < 1e-12:
                break

        # Phase 2: Aggressive position refinement
        for opt_iteration in range(200):
            improvement_found = False

            for i in range(26):
                x, y, r = circles[i]
                current_radius = r
                best_radius = current_radius
                best_config = (x, y, r)

                # Adaptive step size: larger steps early, smaller steps later
                step_base = 0.0025 * (1.0 - cycle / 4.0) * (1.0 - opt_iteration / 200.0)

                # Extended 5x5 neighborhood search (25 positions)
                for dx_factor in range(-2, 3):
                    for dy_factor in range(-2, 3):
                        if dx_factor == 0 and dy_factor == 0:
                            continue

                        nx = x + dx_factor * step_base
                        ny = y + dy_factor * step_base

                        if 0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0:
                            new_radius = get_max_radius(nx, ny, circles, i)

                            if new_radius > best_radius + 1e-10:
                                best_radius = new_radius
                                best_config = (nx, ny, new_radius)
                                improvement_found = True

                circles[i] = list(best_config)

            if not improvement_found:
                break

    return circles

def main():
    random.seed(456)

    best_circles = None
    best_score = 0.0

    # Try multiple initialization patterns
    init_patterns = []

    # Pattern 1: 6x5 grid (original champion pattern)
    pattern1 = []
    for row in range(5):
        for col in range(6):
            if len(pattern1) < 26:
                x = (col + 0.5) / 6.0
                y = (row + 0.5) / 5.0
                pattern1.append([x, y, 0.0])
    init_patterns.append(pattern1)

    # Pattern 2: 5x6 grid (transposed orientation)
    pattern2 = []
    for row in range(6):
        for col in range(5):
            if len(pattern2) < 26:
                x = (col + 0.5) / 5.0
                y = (row + 0.5) / 6.0
                pattern2.append([x, y, 0.0])
    init_patterns.append(pattern2)

    # Pattern 3: Hexagonal-inspired packing
    pattern3 = []
    for row in range(7):
        for col in range(4):
            if len(pattern3) < 26:
                # Offset alternate rows for hexagonal effect
                x = (col + 0.5 + (0.25 if row % 2 == 1 else 0.0)) / 4.5
                y = (row + 0.5) / 7.5
                if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                    pattern3.append([x, y, 0.0])

    # Pad pattern3 if needed
    while len(pattern3) < 26:
        pattern3.append([random.uniform(0.05, 0.95), random.uniform(0.05, 0.95), 0.0])
    pattern3 = pattern3[:26]
    init_patterns.append(pattern3)

    # Optimize each pattern
    for init_circles in init_patterns:
        circles = optimize_config(init_circles)

        # Validate solution
        valid = True
        for i, (x, y, r) in enumerate(circles):
            if x - r < -1e-9 or x + r > 1.0 + 1e-9 or y - r < -1e-9 or y + r > 1.0 + 1e-9:
                valid = False
                break

            for j in range(i + 1, 26):
                x2, y2, r2 = circles[j]
                dist = math.sqrt((x - x2) ** 2 + (y - y2) ** 2)
                if dist < r + r2 - 1e-9:
                    valid = False
                    break

            if not valid:
                break

        if valid:
            total_radius = sum(r for x, y, r in circles)
            if total_radius > best_score:
                best_score = total_radius
                best_circles = circles

    # Final validation of best solution
    if best_circles:
        for i, (x, y, r) in enumerate(best_circles):
            assert x - r >= -1e-9, f"Circle {i} violates left bound"
            assert x + r <= 1.0 + 1e-9, f"Circle {i} violates right bound"
            assert y - r >= -1e-9, f"Circle {i} violates bottom bound"
            assert y + r <= 1.0 + 1e-9, f"Circle {i} violates top bound"

            for j in range(i + 1, 26):
                x2, y2, r2 = best_circles[j]
                dist = math.sqrt((x - x2) ** 2 + (y - y2) ** 2)
                assert dist >= r + r2 - 1e-9, f"Circles {i} and {j} overlap"

    print(best_circles)

if __name__ == "__main__":
    main()
