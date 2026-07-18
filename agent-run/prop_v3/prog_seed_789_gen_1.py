import math
import random

def solve():
    random.seed(789)

    # Initialize with 6x5 grid - deterministic placement for 26 circles
    circles = []
    for row in range(5):
        for col in range(6):
            x = (col + 0.5) / 6.0
            y = (row + 0.5) / 5.0
            circles.append([x, y, 0.01])

    # Phase 1: Grow radii to maximum non-overlapping size
    for iteration in range(50):
        improved = False
        for i in range(26):
            # Max radius limited by boundary
            max_r = min(circles[i][0], 1 - circles[i][0],
                       circles[i][1], 1 - circles[i][1])

            # Max radius limited by other circles
            for j in range(26):
                if i != j:
                    dx = circles[i][0] - circles[j][0]
                    dy = circles[i][1] - circles[j][1]
                    dist = math.sqrt(dx * dx + dy * dy)
                    max_r = min(max_r, dist - circles[j][2])

            max_r = max(max_r - 1e-9, 0)
            if max_r > circles[i][2]:
                circles[i][2] = max_r
                improved = True

        if not improved:
            break

    # Phase 2: Iteratively adjust positions and re-grow radii
    for iteration in range(150):
        old_sum = sum(c[2] for c in circles)

        # Random position adjustments with decreasing step size
        step = 0.005 * (1.0 - iteration / 150.0)

        for i in range(26):
            dx = (random.random() - 0.5) * step * 2.0
            dy = (random.random() - 0.5) * step * 2.0

            new_x = circles[i][0] + dx
            new_y = circles[i][1] + dy

            # Clip to allow for current radius (keep circle in bounds)
            new_x = max(circles[i][2], min(1.0 - circles[i][2], new_x))
            new_y = max(circles[i][2], min(1.0 - circles[i][2], new_y))

            # Check for collisions with other circles
            valid = True
            for j in range(26):
                if i != j:
                    dx2 = new_x - circles[j][0]
                    dy2 = new_y - circles[j][1]
                    dist = math.sqrt(dx2 * dx2 + dy2 * dy2)
                    min_dist = circles[i][2] + circles[j][2] - 1e-9
                    if dist < min_dist:
                        valid = False
                        break

            # Accept position if valid
            if valid:
                circles[i][0] = new_x
                circles[i][1] = new_y

        # After position updates, grow radii again
        for i in range(26):
            max_r = min(circles[i][0], 1.0 - circles[i][0],
                       circles[i][1], 1.0 - circles[i][1])

            for j in range(26):
                if i != j:
                    dx = circles[i][0] - circles[j][0]
                    dy = circles[i][1] - circles[j][1]
                    dist = math.sqrt(dx * dx + dy * dy)
                    max_r = min(max_r, dist - circles[j][2])

            max_r = max(max_r - 1e-9, 0)
            if max_r > circles[i][2]:
                circles[i][2] = max_r

        new_sum = sum(c[2] for c in circles)

        # Stop if convergence reached
        if new_sum - old_sum < 1e-9 and iteration > 50:
            break

    return circles

result = solve()
print(result)
