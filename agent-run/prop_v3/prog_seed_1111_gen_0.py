import math
import random
import itertools

def solve():
    random.seed(1111)

    n = 26

    # Initialize positions on a 6x5 grid (baseline config)
    positions = []
    for i in range(5):
        for j in range(6):
            if len(positions) < n:
                x = (j + 0.5) / 6.0
                y = (i + 0.5) / 5.0
                positions.append([x, y])

    # Initialize small radii
    radii = [1e-6] * n

    # ===== GROWTH PHASE: Iteratively increase radii =====
    # This is the core optimization: for each circle, find the maximum
    # radius allowed by boundaries and non-overlap constraints

    for iteration in range(300):
        improved = False

        for i in range(n):
            x, y = positions[i]
            current_r = radii[i]

            # Compute max radius from boundary constraints
            max_r = min(x, y, 1.0 - x, 1.0 - y)

            # Compute max radius from non-overlap constraints with all other circles
            for j in range(n):
                if i != j:
                    xj, yj = positions[j]
                    rj = radii[j]

                    dist = math.sqrt((x - xj)**2 + (y - yj)**2)

                    # Non-overlap: dist >= current_r + rj
                    # Therefore: current_r <= dist - rj
                    if dist > rj:
                        max_r = min(max_r, dist - rj)
                    else:
                        max_r = 0.0

            # Conservatively grow the radius
            if max_r > current_r:
                new_r = current_r + (max_r - current_r) * 0.95
                radii[i] = max(current_r, new_r)
                improved = True

        # Early termination if no improvement
        if not improved and iteration > 50:
            break

    # ===== POSITION REFINEMENT PHASE =====
    # Optionally relax positions to create better packing
    # Use a simple "push away" approach

    for ref_iteration in range(50):
        for i in range(n):
            x, y = positions[i]
            fx, fy = 0.0, 0.0

            # Repulsive forces from other circles
            for j in range(n):
                if i != j:
                    xj, yj = positions[j]
                    dx = x - xj
                    dy = y - yj
                    dist = math.sqrt(dx*dx + dy*dy)

                    if dist > 1e-6:
                        # Repulsion strength
                        force = 0.01 / (dist * dist + 1e-3)
                        fx += (dx / dist) * force
                        fy += (dy / dist) * force

            # Attractive force to center of square
            center_x, center_y = 0.5, 0.5
            dx = center_x - x
            dy = center_y - y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 1e-6:
                attraction = 0.0001
                fx += (dx / dist) * attraction
                fy += (dy / dist) * attraction

            # Apply forces with boundary constraint
            new_x = x + fx
            new_y = y + fy

            # Clamp to stay inside and away from boundaries
            margin = 0.001
            new_x = max(margin, min(1.0 - margin, new_x))
            new_y = max(margin, min(1.0 - margin, new_y))

            positions[i] = [new_x, new_y]

        # Re-optimize radii after position change
        for _ in range(10):
            for i in range(n):
                x, y = positions[i]
                current_r = radii[i]

                max_r = min(x, y, 1.0 - x, 1.0 - y)

                for j in range(n):
                    if i != j:
                        xj, yj = positions[j]
                        rj = radii[j]
                        dist = math.sqrt((x - xj)**2 + (y - yj)**2)
                        if dist > rj:
                            max_r = min(max_r, dist - rj)
                        else:
                            max_r = 0.0

                if max_r > current_r:
                    new_r = current_r + (max_r - current_r) * 0.98
                    radii[i] = new_r

    # ===== FINAL POLISH: Aggressive radius growth =====

    for final_iteration in range(50):
        for i in range(n):
            x, y = positions[i]
            current_r = radii[i]

            max_r = min(x, y, 1.0 - x, 1.0 - y)

            for j in range(n):
                if i != j:
                    xj, yj = positions[j]
                    rj = radii[j]
                    dist = math.sqrt((x - xj)**2 + (y - yj)**2)
                    if dist > rj:
                        max_r = min(max_r, dist - rj)
                    else:
                        max_r = 0.0

            # Be slightly more aggressive in final phase
            if max_r > current_r:
                radii[i] = current_r + (max_r - current_r) * 0.97

    # ===== BUILD OUTPUT =====
    result = []
    for i in range(n):
        result.append([positions[i][0], positions[i][1], radii[i]])

    return result

# Solve and print
circles = solve()
print(circles)
