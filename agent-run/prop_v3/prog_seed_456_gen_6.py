import random
import math
import itertools

def get_max_radius(x, y, circles, i):
    """Get maximum radius for circle i at position (x, y) without violating constraints."""
    r_max = min(x, 1.0 - x, y, 1.0 - y)

    for j, (x2, y2, r2) in enumerate(circles):
        if i != j:
            dist = math.sqrt((x - x2) ** 2 + (y - y2) ** 2)
            r_max = min(r_max, max(0.0, dist - r2))

    return max(0.0, r_max)

def optimize_radii_aggressive(circles, max_iterations=8000):
    """Very aggressive radius growth with tight convergence."""
    circles = [list(c) for c in circles]

    for iteration in range(max_iterations):
        max_growth = 0.0
        for i in range(26):
            x, y, r = circles[i]
            new_r = get_max_radius(x, y, circles, i)
            growth = new_r - r
            max_growth = max(max_growth, growth)
            circles[i][2] = new_r

        if max_growth < 1e-16:
            break

    return circles

def optimize_positions_local(circles, max_opt_iterations=1500, initial_scale=0.012):
    """Enhanced local position optimization with wider search."""
    circles = [list(c) for c in circles]

    for opt_iter in range(max_opt_iterations):
        improvement_found = False
        base_step_size = initial_scale * (1.0 - 0.85 * opt_iter / max_opt_iterations)

        for i in range(26):
            x, y, r = circles[i]
            current_radius = r
            best_radius = current_radius
            best_config = (x, y, r)

            # Wider search space with finer granularity
            for dx_factor in range(-6, 7):
                for dy_factor in range(-6, 7):
                    if dx_factor == 0 and dy_factor == 0:
                        continue

                    step_size = base_step_size
                    nx = x + dx_factor * step_size
                    ny = y + dy_factor * step_size

                    if 0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0:
                        new_radius = get_max_radius(nx, ny, circles, i)

                        if new_radius > best_radius + 1e-14:
                            best_radius = new_radius
                            best_config = (nx, ny, new_radius)
                            improvement_found = True

            circles[i] = list(best_config)

        if not improvement_found:
            break

    return circles

def optimize_focused_subset(circles, subset_fraction=0.5, iterations=400):
    """Focus optimization on a subset of circles with lowest current radius."""
    circles = [list(c) for c in circles]

    # Sort circles by radius, focus on smaller ones
    indexed_circles = [(i, circles[i][2]) for i in range(26)]
    indexed_circles.sort(key=lambda x: x[1])

    focus_count = max(5, int(26 * subset_fraction))
    focus_indices = [idx[0] for idx in indexed_circles[:focus_count]]

    for iteration in range(iterations):
        max_growth = 0.0

        for i in focus_indices:
            x, y, r = circles[i]
            new_r = get_max_radius(x, y, circles, i)
            growth = new_r - r
            max_growth = max(max_growth, growth)
            circles[i][2] = new_r

        # Try position refinements for focused circles
        for i in focus_indices:
            x, y, r = circles[i]
            best_r = r
            best_x, best_y = x, y

            step = 0.005 * (1.0 - iteration / iterations)
            for dx in [-step, 0, step]:
                for dy in [-step, 0, step]:
                    nx = x + dx
                    ny = y + dy
                    if 0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0:
                        nr = get_max_radius(nx, ny, circles, i)
                        if nr > best_r + 1e-14:
                            best_r = nr
                            best_x, best_y = nx, ny

            circles[i] = [best_x, best_y, best_r]

        if max_growth < 1e-15:
            break

    return circles

def create_optimal_hex_init():
    """Create optimal hexagonal packing initialization."""
    circles = []
    rows = 7
    cols = 4

    for row in range(rows):
        for col in range(cols):
            if len(circles) < 26:
                # Improved hexagonal offset
                offset_x = 0.25 if row % 2 == 1 else 0.0
                x = (col + 0.5 + offset_x) / (cols + 0.35)
                y = (row + 0.5) / (rows + 0.3)

                if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                    circles.append([x, y, 0.0])

    while len(circles) < 26:
        circles.append([random.uniform(0.08, 0.92), random.uniform(0.08, 0.92), 0.0])

    return circles[:26]

def create_dense_grid_init():
    """Create dense grid pattern."""
    circles = []
    # Try 5.2x5 arrangement
    for r in range(7):
        for c in range(4):
            if len(circles) < 26:
                x = 0.1 + c * 0.2
                y = 0.075 + r * 0.13
                if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                    circles.append([x, y, 0.0])

    while len(circles) < 26:
        circles.append([random.uniform(0.1, 0.9), random.uniform(0.1, 0.9), 0.0])

    return circles[:26]

def create_improved_spiral_init():
    """Create improved spiral initialization."""
    circles = []
    cx, cy = 0.5, 0.5

    for i in range(26):
        t = i / 26.0 * 6 * math.pi
        r = 0.4 * (i / 26.0) ** 0.8
        x = cx + r * math.cos(t)
        y = cy + r * math.sin(t)
        x = max(0.05, min(0.95, x))
        y = max(0.05, min(0.95, y))
        circles.append([x, y, 0.0])

    return circles

def create_multi_cluster_init():
    """Create initialization with multiple cluster centers."""
    circles = []
    centers = [
        (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75),
        (0.5, 0.5)
    ]

    for i in range(26):
        center = centers[i % len(centers)]
        cx, cy = center
        angle = 2 * math.pi * (i // len(centers)) / 6
        dist = 0.12 * (1.0 + (i % len(centers)) / len(centers))
        x = cx + dist * math.cos(angle)
        y = cy + dist * math.sin(angle)
        x = max(0.05, min(0.95, x))
        y = max(0.05, min(0.95, y))
        circles.append([x, y, 0.0])

    return circles[:26]

def refine_intensive_multi_phase(circles, num_phases=7):
    """Highly intensive multi-phase refinement."""
    circles = [list(c) for c in circles]

    for phase in range(num_phases):
        # Very aggressive radius iterations
        radius_iters = 1200 + phase * 600
        circles = optimize_radii_aggressive(circles, max_iterations=radius_iters)

        # Position refinement with adaptive parameters
        search_scale = 0.012 * (1.0 - 0.75 * phase / num_phases)
        pos_iters = 800 - phase * 60
        circles = optimize_positions_local(circles, max_opt_iterations=pos_iters, initial_scale=search_scale)

        # Focused subset optimization on weaker circles
        circles = optimize_focused_subset(circles, subset_fraction=0.6, iterations=300)

    # Intense final tuning with multiple focused passes
    for final_pass in range(4):
        circles = optimize_radii_aggressive(circles, max_iterations=3000)
        circles = optimize_positions_local(circles, max_opt_iterations=500, initial_scale=0.0008)
        circles = optimize_focused_subset(circles, subset_fraction=0.8, iterations=200)

    return circles

def validate_solution(circles):
    """Validate that a solution is valid."""
    if len(circles) != 26:
        return False

    for i, (x, y, r) in enumerate(circles):
        if x - r < -1e-9 or x + r > 1.0 + 1e-9:
            return False
        if y - r < -1e-9 or y + r > 1.0 + 1e-9:
            return False

        for j in range(i + 1, 26):
            x2, y2, r2 = circles[j]
            dist = math.sqrt((x - x2) ** 2 + (y - y2) ** 2)
            if dist < r + r2 - 1e-9:
                return False

    return True

def score_solution(circles):
    """Compute score for a solution."""
    return sum(r for x, y, r in circles)

def main():
    random.seed(456)

    best_circles = None
    best_score = 0.0

    # Initialize with diverse and improved patterns
    init_patterns = []

    # Pattern 1: Optimal hexagonal
    init_patterns.append(create_optimal_hex_init())

    # Pattern 2: Dense grid
    init_patterns.append(create_dense_grid_init())

    # Pattern 3-4: Improved grids with different aspect ratios
    for rows, cols in [(6, 5), (5, 6)]:
        circles = []
        for r in range(rows):
            for c in range(cols):
                if len(circles) < 26:
                    offset = 0.12 if r % 2 == 1 else 0.0
                    x = (c + 0.5 + offset) / (cols + 0.25)
                    y = (r + 0.5) / (rows + 0.3)
                    if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                        circles.append([x, y, 0.0])
        while len(circles) < 26:
            circles.append([random.uniform(0.1, 0.9), random.uniform(0.1, 0.9), 0.0])
        init_patterns.append(circles[:26])

    # Pattern 5: Improved spiral
    init_patterns.append(create_improved_spiral_init())

    # Pattern 6: Multi-cluster
    init_patterns.append(create_multi_cluster_init())

    # Optimize each pattern with intensive refinement
    for pattern_idx, init_circles in enumerate(init_patterns):
        circles = refine_intensive_multi_phase(init_circles, num_phases=7)

        # Validate solution
        if validate_solution(circles):
            total_radius = score_solution(circles)
            if total_radius > best_score:
                best_score = total_radius
                best_circles = circles

    # Aggressive perturbation loop with focused re-optimization
    if best_circles:
        for perturbation_iter in range(10):
            perturbation_amount = 0.025 * (1.0 - perturbation_iter / 10.0)
            perturbed = []
            for x, y, r in best_circles:
                nx = x + random.uniform(-perturbation_amount, perturbation_amount)
                ny = y + random.uniform(-perturbation_amount, perturbation_amount)
                nx = max(0.01, min(0.99, nx))
                ny = max(0.01, min(0.99, ny))
                perturbed.append([nx, ny, 0.0])

            circles = refine_intensive_multi_phase(perturbed, num_phases=5)

            if validate_solution(circles):
                total_radius = score_solution(circles)
                if total_radius > best_score:
                    best_score = total_radius
                    best_circles = circles

    # Final validation and output
    if best_circles and validate_solution(best_circles):
        print(best_circles)
    else:
        print([[0.5, 0.5, 0.0]] * 26)

if __name__ == "__main__":
    main()
