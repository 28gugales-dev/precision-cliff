import random
import math

def get_max_radius(x, y, circles, i):
    """Get maximum radius for circle i at position (x, y) without violating constraints."""
    # Constraint from unit square walls
    r_max = min(x, 1.0 - x, y, 1.0 - y)

    # Constraint from all other circles
    for j, (x2, y2, r2) in enumerate(circles):
        if i != j:
            dist = math.sqrt((x - x2) ** 2 + (y - y2) ** 2)
            # r_i + r_j <= dist, so r_i <= dist - r_j
            r_max = min(r_max, max(0.0, dist - r2))

    return max(0.0, r_max)

def main():
    random.seed(456)

    # Initialize with 6x5 grid layout (26 circles total)
    circles = []
    for row in range(5):
        for col in range(6):
            if len(circles) < 26:
                x = (col + 0.5) / 6.0
                y = (row + 0.5) / 5.0
                circles.append([x, y, 0.0])

    # Phase 1: Iteratively grow all radii
    for iteration in range(500):
        max_growth = 0.0
        for i in range(26):
            x, y, r = circles[i]
            new_r = get_max_radius(x, y, circles, i)
            growth = new_r - r
            max_growth = max(max_growth, growth)
            circles[i][2] = new_r

        # Stop if no meaningful growth
        if max_growth < 1e-12:
            break

    # Phase 2: Position refinement - try to move circles to better locations
    for opt_phase in range(100):
        improvement_found = False

        for i in range(26):
            x, y, r = circles[i]

            # Current score for this circle
            current_score = r
            best_score = current_score
            best_config = (x, y, r)

            # Try small movements in a 3x3 neighborhood
            for dx_factor in [-1, 0, 1]:
                for dy_factor in [-1, 0, 1]:
                    if dx_factor == 0 and dy_factor == 0:
                        continue

                    # Use adaptive step size
                    step = 0.001 * (1.0 + opt_phase / 100.0)
                    nx = x + dx_factor * step
                    ny = y + dy_factor * step

                    # Check if new position is valid
                    if 0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0:
                        new_r = get_max_radius(nx, ny, circles, i)

                        if new_r > best_score + 1e-10:
                            best_score = new_r
                            best_config = (nx, ny, new_r)
                            improvement_found = True

            # Update circle if better configuration found
            if best_config != (x, y, r):
                circles[i] = list(best_config)

        # If no improvement found, exit optimization phase
        if not improvement_found:
            break

    # Phase 3: Final aggressive growth pass
    for iteration in range(500):
        max_growth = 0.0
        for i in range(26):
            x, y, r = circles[i]
            new_r = get_max_radius(x, y, circles, i)
            growth = new_r - r
            max_growth = max(max_growth, growth)
            circles[i][2] = new_r

        if max_growth < 1e-12:
            break

    # Validate solution
    total_radius = 0.0
    for i, (x, y, r) in enumerate(circles):
        # Check bounds
        assert x - r >= -1e-9, f"Circle {i} violates left bound"
        assert x + r <= 1.0 + 1e-9, f"Circle {i} violates right bound"
        assert y - r >= -1e-9, f"Circle {i} violates bottom bound"
        assert y + r <= 1.0 + 1e-9, f"Circle {i} violates top bound"

        # Check no overlaps
        for j in range(i + 1, 26):
            x2, y2, r2 = circles[j]
            dist = math.sqrt((x - x2) ** 2 + (y - y2) ** 2)
            assert dist >= r + r2 - 1e-9, f"Circles {i} and {j} overlap"

        total_radius += r

    # Output result
    print(circles)

if __name__ == "__main__":
    main()
