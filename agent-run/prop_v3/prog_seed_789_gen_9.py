import math
import random

def pack_circles():
    """Pack 26 circles in unit square, maximizing sum of radii."""
    random.seed(789)

    circles = []

    # Phase 1: Intelligent grid placement with space optimization
    grid_positions = []

    # Multi-scale grid for better coverage
    for scale in [12, 8]:
        for i in range(scale):
            for j in range(scale):
                x = 0.03 + i * (0.94 / max(1, scale - 1))
                y = 0.03 + j * (0.94 / max(1, scale - 1))
                grid_positions.append((x, y))

    # Remove duplicates and add random jitter for diversity
    unique_positions = list(set(grid_positions))
    for pos in unique_positions[:26]:
        grid_positions.append((pos[0] + random.uniform(-0.01, 0.01),
                               pos[1] + random.uniform(-0.01, 0.01)))

    # Greedy placement with size adaptation
    for circle_idx in range(26):
        candidates = []

        # Grid candidates
        num_grid = 150 - circle_idx * 3
        for _ in range(min(num_grid, len(grid_positions))):
            idx = random.randint(0, len(grid_positions) - 1)
            x, y = grid_positions[idx]
            x = max(0.005, min(0.995, x + random.uniform(-0.015, 0.015)))
            y = max(0.005, min(0.995, y + random.uniform(-0.015, 0.015)))
            candidates.append((x, y))

        # Strategic random sampling - focus on uncovered areas
        num_random = 400 - circle_idx * 12
        for _ in range(max(100, num_random)):
            x = random.uniform(0.005, 0.995)
            y = random.uniform(0.005, 0.995)
            candidates.append((x, y))

        # Find best position
        best_circle = None
        best_r = 0
        for x, y in candidates:
            r_max = compute_max_radius(x, y, circles)
            if r_max > best_r and r_max > 1e-8:
                best_r = r_max
                best_circle = [x, y, r_max]

        if best_circle:
            circles.append(best_circle)

    # Phase 2: Aggressive position refinement with multiple passes
    max_iterations = 20
    for iteration in range(max_iterations):
        base_step = 0.015 * (1.0 - iteration / (max_iterations + 1))
        improved = False

        for idx in range(len(circles)):
            x, y, r = circles[idx]
            current_score = sum(c[2] for c in circles)
            best_score = current_score
            best_x, best_y = x, y

            # Extended search with finer gradations
            step_sizes = [-base_step, -base_step*0.6, -base_step*0.3, 0,
                         base_step*0.3, base_step*0.6, base_step]
            for dx in step_sizes:
                for dy in step_sizes:
                    if dx == 0 and dy == 0:
                        continue
                    nx = x + dx
                    ny = y + dy
                    if 0.0005 <= nx <= 0.9995 and 0.0005 <= ny <= 0.9995:
                        nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                        new_score = current_score - r + nr
                        if new_score > best_score + 1e-12:
                            best_score = new_score
                            best_x, best_y = nx, ny
                            improved = True

            if (best_x, best_y) != (x, y):
                circles[idx][0] = best_x
                circles[idx][1] = best_y
                circles[idx][2] = compute_max_radius(best_x, best_y, circles, skip_idx=idx)

        if not improved and iteration > 8:
            break

    # Phase 3: Diagonal and radial search refinement
    for iteration in range(12):
        step = 0.008 * (1.0 - iteration / 12.0)

        for idx in range(len(circles)):
            x, y, r = circles[idx]
            current_score = sum(c[2] for c in circles)
            best_score = current_score
            best_x, best_y = x, y

            # Diagonal search patterns
            diagonals = [
                (step, step), (-step, step), (step, -step), (-step, -step),
                (step, 0), (-step, 0), (0, step), (0, -step),
                (step*0.7, step*0.7), (-step*0.7, step*0.7),
                (step*0.7, -step*0.7), (-step*0.7, -step*0.7)
            ]

            for dx, dy in diagonals:
                nx = x + dx
                ny = y + dy
                if 0.0005 <= nx <= 0.9995 and 0.0005 <= ny <= 0.9995:
                    nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                    new_score = current_score - r + nr
                    if new_score > best_score + 1e-12:
                        best_score = new_score
                        best_x, best_y = nx, ny

            if (best_x, best_y) != (x, y):
                circles[idx][0] = best_x
                circles[idx][1] = best_y
                circles[idx][2] = compute_max_radius(best_x, best_y, circles, skip_idx=idx)

    # Phase 4: Radius maximization pass
    for idx in range(len(circles)):
        x, y = circles[idx][:2]
        circles[idx][2] = compute_max_radius(x, y, circles, skip_idx=idx)

    # Phase 5: Fine-grained pairwise optimization
    for iteration in range(10):
        improved = False
        for i in range(len(circles)):
            for j in range(i + 1, len(circles)):
                # Try swapping or adjusting these two circles
                xi, yi, ri = circles[i]
                xj, yj, rj = circles[j]

                current_score = ri + rj

                # Try small adjustments to both
                for di in [-0.003, 0, 0.003]:
                    for dj in [-0.003, 0, 0.003]:
                        nxi = xi + di
                        nyi = yi + di
                        nxj = xj + dj
                        nyj = yj + dj

                        if (0.0005 <= nxi <= 0.9995 and 0.0005 <= nyi <= 0.9995 and
                            0.0005 <= nxj <= 0.9995 and 0.0005 <= nyj <= 0.9995):

                            temp_circles = circles[:]
                            temp_circles[i] = [nxi, nyi, 0]
                            temp_circles[j] = [nxj, nyj, 0]

                            nri = compute_max_radius(nxi, nyi, temp_circles, skip_idx=i)
                            nrj = compute_max_radius(nxj, nyj, temp_circles, skip_idx=j)
                            new_score = nri + nrj

                            if new_score > current_score + 1e-12:
                                circles[i][0] = nxi
                                circles[i][1] = nyi
                                circles[i][2] = nri
                                circles[j][0] = nxj
                                circles[j][1] = nyj
                                circles[j][2] = nrj
                                improved = True

        if not improved:
            break

    # Phase 6: Ultra-fine radius optimization
    for idx in range(len(circles)):
        x, y = circles[idx][:2]
        circles[idx][2] = compute_max_radius(x, y, circles, skip_idx=idx)

    # Phase 7: Micro-position refinement
    for iteration in range(8):
        step = 0.002 * (1.0 - iteration / 8.0)

        for idx in range(len(circles)):
            x, y, r = circles[idx]
            current_score = sum(c[2] for c in circles)
            best_score = current_score
            best_x, best_y = x, y

            for dx in [-step, 0, step]:
                for dy in [-step, 0, step]:
                    if dx == 0 and dy == 0:
                        continue
                    nx = x + dx
                    ny = y + dy
                    if 0.0005 <= nx <= 0.9995 and 0.0005 <= ny <= 0.9995:
                        nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                        new_score = current_score - r + nr
                        if new_score > best_score + 1e-12:
                            best_score = new_score
                            best_x, best_y = nx, ny

            if (best_x, best_y) != (x, y):
                circles[idx][0] = best_x
                circles[idx][1] = best_y
                circles[idx][2] = compute_max_radius(best_x, best_y, circles, skip_idx=idx)

    # Phase 8: Final radius maximization
    for idx in range(len(circles)):
        x, y = circles[idx][:2]
        circles[idx][2] = compute_max_radius(x, y, circles, skip_idx=idx)

    return circles

def compute_max_radius(x, y, circles, skip_idx=-1):
    """Compute the maximum radius for a circle at (x, y) without overlaps."""
    # Boundary constraints with small safety margin
    r_max = min(x, y, 1.0 - x, 1.0 - y)

    # Non-overlap constraints with existing circles
    for i, (cx, cy, cr) in enumerate(circles):
        if i == skip_idx:
            continue
        dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        r_max = min(r_max, max(0.0, dist - cr))

    return max(0.0, r_max)

def validate_geometry(circles):
    """Validate that the packing is geometrically valid."""
    if len(circles) != 26:
        return False

    # Boundary constraints
    for x, y, r in circles:
        if r < 0 or x - r < -1e-9 or x + r > 1.0 + 1e-9:
            return False
        if y - r < -1e-9 or y + r > 1.0 + 1e-9:
            return False

    # Non-overlap constraints
    for i, (x1, y1, r1) in enumerate(circles):
        for x2, y2, r2 in circles[i + 1:]:
            dist = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
            if dist < r1 + r2 - 1e-9:
                return False

    return True

# Generate and validate the packing
result = pack_circles()

# Minimal shrinking only if validation fails
if not validate_geometry(result):
    for circle in result:
        circle[2] *= 0.95

print(result)
