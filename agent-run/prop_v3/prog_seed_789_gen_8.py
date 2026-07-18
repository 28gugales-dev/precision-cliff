import math
import random

def pack_circles():
    """Pack 26 circles in unit square, maximizing sum of radii."""
    random.seed(789)

    circles = []

    # Phase 1: Strategic greedy placement with enhanced candidate generation
    for circle_idx in range(26):
        candidates = []

        # Multi-scale grid sampling
        for grid_density in [12, 8, 5]:
            if grid_density > 1:
                step = 0.9 / (grid_density - 1)
                for i in range(grid_density):
                    for j in range(grid_density):
                        x = 0.05 + i * step
                        y = 0.05 + j * step
                        candidates.append((x, y))

        # Random candidates biased toward less dense regions
        num_random = max(100, 400 - circle_idx * 12)
        for _ in range(num_random):
            # Prefer regions away from existing circles
            found_good = False
            for attempt in range(5):
                x = random.uniform(0.005, 0.995)
                y = random.uniform(0.005, 0.995)

                min_dist_to_existing = float('inf')
                for cx, cy, _ in circles:
                    dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                    min_dist_to_existing = min(min_dist_to_existing, dist)

                if circle_idx == 0 or min_dist_to_existing > 0.15:
                    candidates.append((x, y))
                    found_good = True
                    break

            if not found_good and circle_idx > 0:
                candidates.append((random.uniform(0.005, 0.995), random.uniform(0.005, 0.995)))

        # Find best position
        best_circle = None
        best_r = 0
        for x, y in candidates:
            r_max = compute_max_radius(x, y, circles)
            if r_max > best_r and r_max > 1e-9:
                best_r = r_max
                best_circle = [x, y, r_max]

        if best_circle:
            circles.append(best_circle)

    # Phase 2: Aggressive position refinement with adaptive step sizes
    for iteration in range(25):
        step = 0.015 * (1.0 - iteration / 25.0)
        improved = False
        improvement_count = 0

        for idx in range(len(circles)):
            x, y, r = circles[idx]
            current_score = sum(c[2] for c in circles)
            best_score = current_score
            best_x, best_y = x, y

            # Dense neighborhood search
            offsets = []
            for dx in [-step, -step*0.6, -step*0.3, 0, step*0.3, step*0.6, step]:
                for dy in [-step, -step*0.6, -step*0.3, 0, step*0.3, step*0.6, step]:
                    if dx != 0 or dy != 0:
                        offsets.append((dx, dy))

            for dx, dy in offsets:
                nx = x + dx
                ny = y + dy
                if 0.0003 <= nx <= 0.9997 and 0.0003 <= ny <= 0.9997:
                    nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                    new_score = current_score - r + nr
                    if new_score > best_score + 1e-13:
                        best_score = new_score
                        best_x, best_y = nx, ny
                        improved = True
                        improvement_count += 1

            if (best_x, best_y) != (x, y):
                circles[idx][0] = best_x
                circles[idx][1] = best_y
                circles[idx][2] = compute_max_radius(best_x, best_y, circles, skip_idx=idx)

        if not improved and iteration > 10:
            break

    # Phase 3: Radius maximization after position optimization
    for idx in range(len(circles)):
        x, y = circles[idx][:2]
        circles[idx][2] = compute_max_radius(x, y, circles, skip_idx=idx)

    # Phase 4: Ultra-fine position refinement with very small steps
    for iteration in range(12):
        step = 0.004 * (1.0 - iteration / 12.0)

        for idx in range(len(circles)):
            x, y, r = circles[idx]
            current_score = sum(c[2] for c in circles)
            best_score = current_score
            best_x, best_y = x, y

            for dx in [-step, -step*0.5, 0, step*0.5, step]:
                for dy in [-step, -step*0.5, 0, step*0.5, step]:
                    if dx == 0 and dy == 0:
                        continue
                    nx = x + dx
                    ny = y + dy
                    if 0.0003 <= nx <= 0.9997 and 0.0003 <= ny <= 0.9997:
                        nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                        new_score = current_score - r + nr
                        if new_score > best_score + 1e-13:
                            best_score = new_score
                            best_x, best_y = nx, ny

            if (best_x, best_y) != (x, y):
                circles[idx][0] = best_x
                circles[idx][1] = best_y
                circles[idx][2] = compute_max_radius(best_x, best_y, circles, skip_idx=idx)

    # Phase 5: Perturbation and re-optimization - escape local optima
    for perturb_round in range(3):
        perturb_magnitude = 0.008 * (1.0 - perturb_round / 3.0)

        # Perturb positions
        for idx in range(len(circles)):
            if random.random() < 0.6:
                dx = random.uniform(-perturb_magnitude, perturb_magnitude)
                dy = random.uniform(-perturb_magnitude, perturb_magnitude)
                nx = circles[idx][0] + dx
                ny = circles[idx][1] + dy

                if 0.0003 <= nx <= 0.9997 and 0.0003 <= ny <= 0.9997:
                    nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                    old_r = circles[idx][2]
                    if nr > old_r * 0.95:  # Accept if not too much worse
                        circles[idx][0] = nx
                        circles[idx][1] = ny
                        circles[idx][2] = nr

        # Local re-optimization after perturbation
        for iteration in range(5):
            step = 0.005 * (1.0 - iteration / 5.0)

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
                        if 0.0003 <= nx <= 0.9997 and 0.0003 <= ny <= 0.9997:
                            nr = compute_max_radius(nx, ny, circles, skip_idx=idx)
                            new_score = current_score - r + nr
                            if new_score > best_score + 1e-13:
                                best_score = new_score
                                best_x, best_y = nx, ny

                if (best_x, best_y) != (x, y):
                    circles[idx][0] = best_x
                    circles[idx][1] = best_y
                    circles[idx][2] = compute_max_radius(best_x, best_y, circles, skip_idx=idx)

    # Phase 6: Final radius maximization pass
    for idx in range(len(circles)):
        x, y = circles[idx][:2]
        circles[idx][2] = compute_max_radius(x, y, circles, skip_idx=idx)

    # Phase 7: Final cleanup - ensure all circles are valid and shrink if needed
    for idx in range(len(circles)):
        r = circles[idx][2]
        if r < 1e-9:
            circles[idx][2] = 0.0

    return circles

def compute_max_radius(x, y, circles, skip_idx=-1):
    """Compute the maximum radius for a circle at (x, y) without overlaps."""
    # Boundary constraints
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
        if r < 0 or x - r < -1e-8 or x + r > 1.0 + 1e-8:
            return False
        if y - r < -1e-8 or y + r > 1.0 + 1e-8:
            return False

    # Non-overlap constraints
    for i, (x1, y1, r1) in enumerate(circles):
        for x2, y2, r2 in circles[i + 1:]:
            dist = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
            if dist < r1 + r2 - 1e-8:
                return False

    return True

# Generate the packing
result = pack_circles()

# Conservative shrinking only if validation fails
if not validate_geometry(result):
    for circle in result:
        circle[2] *= 0.96

print(result)
