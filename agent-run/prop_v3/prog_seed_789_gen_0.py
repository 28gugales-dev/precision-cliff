import math
import random

def main():
    random.seed(789)

    # Initialize 26 circles on a 6x5 grid
    circles = []
    for i in range(5):
        for j in range(6):
            x = (j + 0.5) / 6.0
            y = (i + 0.5) / 5.0
            circles.append([x, y, 0.01])

    # Phase 1: Iteratively grow all radii until convergence
    for iteration in range(5000):
        any_growth = False

        for i in range(26):
            x, y, r = circles[i]

            # Maximum radius before hitting boundary
            max_r = min(x, y, 1.0 - x, 1.0 - y)

            # Maximum radius before hitting other circles
            for j in range(26):
                if i != j:
                    xj, yj, rj = circles[j]
                    dist = math.sqrt((x - xj) ** 2 + (y - yj) ** 2)
                    max_r = min(max_r, dist - rj)

            # Grow radius conservatively
            if max_r > r:
                delta = min(0.0002, max_r - r)
                circles[i][2] = r + delta
                any_growth = True

        if not any_growth:
            break

    # Phase 2: Fine-tune positions with local search
    for iteration in range(200):
        for i in range(26):
            x, y, r = circles[i]
            best_config = (x, y, r)
            best_score = r

            # Try small perturbations in position
            for dx in [-0.003, -0.001, 0, 0.001, 0.003]:
                for dy in [-0.003, -0.001, 0, 0.001, 0.003]:
                    nx, ny = x + dx, y + dy

                    # Check bounds
                    if nx - r < 0 or nx + r > 1.0 or ny - r < 0 or ny + r > 1.0:
                        continue

                    # Check overlap with other circles
                    valid = True
                    for j in range(26):
                        if i != j:
                            xj, yj, rj = circles[j]
                            dist = math.sqrt((nx - xj) ** 2 + (ny - yj) ** 2)
                            if dist < r + rj - 1e-9:
                                valid = False
                                break

                    if valid:
                        # Compute maximum new radius at this position
                        new_max_r = min(nx, ny, 1.0 - nx, 1.0 - ny)
                        for j in range(26):
                            if i != j:
                                xj, yj, rj = circles[j]
                                dist = math.sqrt((nx - xj) ** 2 + (ny - yj) ** 2)
                                new_max_r = min(new_max_r, dist - rj)

                        new_r = min(r, new_max_r)
                        if new_r > best_score:
                            best_config = (nx, ny, new_r)
                            best_score = new_r

            circles[i][0] = best_config[0]
            circles[i][1] = best_config[1]
            circles[i][2] = best_config[2]

    # Phase 3: Final growth pass
    for iteration in range(2000):
        any_growth = False

        for i in range(26):
            x, y, r = circles[i]

            max_r = min(x, y, 1.0 - x, 1.0 - y)

            for j in range(26):
                if i != j:
                    xj, yj, rj = circles[j]
                    dist = math.sqrt((x - xj) ** 2 + (y - yj) ** 2)
                    max_r = min(max_r, dist - rj)

            if max_r > r:
                delta = min(0.0002, max_r - r)
                circles[i][2] = r + delta
                any_growth = True

        if not any_growth:
            break

    return circles

circles = main()
print(circles)
