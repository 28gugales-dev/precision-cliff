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

def optimize_radii_ultra_aggressive(circles, max_iterations=5000):
    """Ultra-aggressive radius growth with tighter convergence."""
    circles = [list(c) for c in circles]

    for iteration in range(max_iterations):
        max_growth = 0.0
        for i in range(26):
            x, y, r = circles[i]
            new_r = get_max_radius(x, y, circles, i)
            growth = new_r - r
            max_growth = max(max_growth, growth)
            circles[i][2] = new_r

        if max_growth < 1e-15:
            break

    return circles

def optimize_positions_enhanced(circles, max_opt_iterations=1200, initial_scale=0.008):
    """Enhanced position optimization with finer-grained search."""
    circles = [list(c) for c in circles]
    momentum = [[0.0, 0.0] for _ in range(26)]
    momentum_alpha = 0.75

    for opt_iter in range(max_opt_iterations):
        improvement_found = False

        # Adaptive step size with slower decay
        base_step_size = initial_scale * (1.0 - 0.8 * opt_iter / max_opt_iterations)
        momentum_factor = momentum_alpha * (1.0 - 0.9 * opt_iter / max_opt_iterations)

        for i in range(26):
            x, y, r = circles[i]
            current_radius = r
            best_radius = current_radius
            best_config = (x, y, r)
            best_move = None

            # Extended 5x5 search for better exploration
            for dx_factor in range(-5, 6):
                for dy_factor in range(-5, 6):
                    if dx_factor == 0 and dy_factor == 0:
                        continue

                    step_size = base_step_size

                    nx = x + (dx_factor * step_size + momentum_factor * momentum[i][0])
                    ny = y + (dy_factor * step_size + momentum_factor * momentum[i][1])

                    if 0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0:
                        new_radius = get_max_radius(nx, ny, circles, i)

                        if new_radius > best_radius + 1e-13:
                            best_radius = new_radius
                            best_config = (nx, ny, new_radius)
                            best_move = (dx_factor * step_size, dy_factor * step_size)
                            improvement_found = True

            circles[i] = list(best_config)

            if best_move:
                momentum[i][0] = best_move[0]
                momentum[i][1] = best_move[1]
            else:
                momentum[i][0] *= 0.85
                momentum[i][1] *= 0.85

        if not improvement_found:
            break

    return circles

def optimize_positions_fine(circles, max_opt_iterations=600, initial_scale=0.0015):
    """Fine-grained position optimization for polishing."""
    circles = [list(c) for c in circles]

    for opt_iter in range(max_opt_iterations):
        improvement_found = False
        base_step_size = initial_scale * (1.0 - 0.9 * opt_iter / max_opt_iterations)

        for i in range(26):
            x, y, r = circles[i]
            current_radius = r
            best_radius = current_radius
            best_config = (x, y, r)

            # Finer 3x3 local search
            for dx_factor in range(-3, 4):
                for dy_factor in range(-3, 4):
                    if dx_factor == 0 and dy_factor == 0:
                        continue

                    nx = x + dx_factor * base_step_size
                    ny = y + dy_factor * base_step_size

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

def refine_aggressive_multi_phase(circles, num_phases=8):
    """Highly aggressive multi-phase refinement with intensive optimization."""
    circles = [list(c) for c in circles]

    for phase in range(num_phases):
        # Increasing radius iterations as we go
        radius_iters = 1000 + phase * 600
        circles = optimize_radii_ultra_aggressive(circles, max_iterations=radius_iters)

        # Position refinement with fine-tuned parameters
        search_scale = 0.009 * (1.0 - 0.75 * phase / (num_phases * 2.0))
        pos_iters = 800 - phase * 40
        circles = optimize_positions_enhanced(circles, max_opt_iterations=pos_iters, initial_scale=search_scale)

    # Intense final tuning with multiple passes
    for final_pass in range(4):
        circles = optimize_radii_ultra_aggressive(circles, max_iterations=3000)
        circles = optimize_positions_enhanced(circles, max_opt_iterations=400, initial_scale=0.0005)
        circles = optimize_positions_fine(circles, max_opt_iterations=300, initial_scale=0.0012)

    return circles

def create_hexagonal_init(density_factor=1.0):
    """Create hexagonal-inspired packing initialization."""
    circles = []
    rows = 7
    cols = 5

    for row in range(rows):
        for col in range(cols):
            if len(circles) < 26:
                x = (col + 0.5 + (0.25 if row % 2 == 1 else 0.0)) / (cols + 0.25)
                y = (row + 0.5) / (rows + 0.5)

                if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                    circles.append([x, y, 0.0])

    while len(circles) < 26:
        circles.append([random.uniform(0.05, 0.95), random.uniform(0.05, 0.95), 0.0])

    return circles[:26]

def create_grid_init(rows, cols):
    """Create rectangular grid initialization."""
    circles = []
    for r in range(rows):
        for c in range(cols):
            if len(circles) < 26:
                x = (c + 0.5) / cols
                y = (r + 0.5) / rows
                circles.append([x, y, 0.0])

    while len(circles) < 26:
        circles.append([random.uniform(0.05, 0.95), random.uniform(0.05, 0.95), 0.0])

    return circles[:26]

def create_perturbed_init(base_circles, perturbation=0.04):
    """Create a perturbed version of base circles."""
    circles = []
    for x, y, r in base_circles:
        nx = x + random.uniform(-perturbation, perturbation)
        ny = y + random.uniform(-perturbation, perturbation)
        nx = max(0.01, min(0.99, nx))
        ny = max(0.01, min(0.99, ny))
        circles.append([nx, ny, 0.0])
    return circles

def create_corner_biased_init():
    """Create initialization with emphasis on corners and edges."""
    circles = []
    # Place circles strategically near corners and edges
    corners = [(0.15, 0.15), (0.85, 0.15), (0.15, 0.85), (0.85, 0.85)]
    edges = [(0.5, 0.1), (0.5, 0.9), (0.1, 0.5), (0.9, 0.5)]

    for cx, cy in corners:
        circles.append([cx, cy, 0.0])

    for ex, ey in edges:
        circles.append([ex, ey, 0.0])

    # Fill remaining with denser grid pattern
    remaining = 26 - len(circles)
    for i in range(remaining):
        row = i // 5
        col = i % 5
        x = 0.2 + col * 0.15
        y = 0.35 + row * 0.15
        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
            circles.append([x, y, 0.0])

    while len(circles) < 26:
        circles.append([random.uniform(0.1, 0.9), random.uniform(0.1, 0.9), 0.0])

    return circles[:26]

def create_spiral_init():
    """Create initialization using a spiral pattern."""
    circles = []
    center_x, center_y = 0.5, 0.5

    for i in range(26):
        t = i / 26.0 * 5 * math.pi
        r = 0.38 * (i / 26.0)
        x = center_x + r * math.cos(t)
        y = center_y + r * math.sin(t)
        x = max(0.05, min(0.95, x))
        y = max(0.05, min(0.95, y))
        circles.append([x, y, 0.0])

    return circles

def create_random_clustered_init():
    """Create initialization with random clusters."""
    circles = []
    num_clusters = 4
    cluster_centers = [(random.uniform(0.25, 0.75), random.uniform(0.25, 0.75)) for _ in range(num_clusters)]

    for i in range(26):
        cluster = cluster_centers[i % num_clusters]
        cx, cy = cluster
        x = cx + random.uniform(-0.15, 0.15)
        y = cy + random.uniform(-0.15, 0.15)
        x = max(0.05, min(0.95, x))
        y = max(0.05, min(0.95, y))
        circles.append([x, y, 0.0])

    return circles

def create_optimized_grid_init():
    """Create optimized grid with better spacing."""
    circles = []
    configs = [(6, 5), (5, 6), (7, 4), (4, 7)]

    rows, cols = configs[0]
    for r in range(rows):
        for c in range(cols):
            if len(circles) < 26:
                offset = 0.15 if r % 2 == 1 else 0.0
                x = (c + 0.5 + offset) / (cols + 0.3)
                y = (r + 0.5) / (rows + 0.3)
                if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                    circles.append([x, y, 0.0])

    while len(circles) < 26:
        circles.append([random.uniform(0.1, 0.9), random.uniform(0.1, 0.9), 0.0])

    return circles[:26]

def create_dense_grid_init():
    """Create denser grid patterns with more aspect ratios."""
    circles = []
    # Try a tighter 5x6 grid
    for r in range(5):
        for c in range(6):
            if len(circles) < 26:
                x = (c + 0.5) / 6.0
                y = (r + 0.5) / 5.0
                circles.append([x, y, 0.0])

    while len(circles) < 26:
        circles.append([random.uniform(0.08, 0.92), random.uniform(0.08, 0.92), 0.0])

    return circles[:26]

def create_uniform_random_init():
    """Create uniform random initialization with spacing constraint."""
    circles = []
    max_attempts = 1000
    min_spacing = 0.05

    for i in range(26):
        placed = False
        for attempt in range(max_attempts):
            x = random.uniform(min_spacing, 1.0 - min_spacing)
            y = random.uniform(min_spacing, 1.0 - min_spacing)

            valid = True
            for (cx, cy, _) in circles:
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < min_spacing:
                    valid = False
                    break

            if valid:
                circles.append([x, y, 0.0])
                placed = True
                break

        if not placed:
            circles.append([random.uniform(0.05, 0.95), random.uniform(0.05, 0.95), 0.0])

    return circles[:26]

def create_center_biased_init():
    """Create initialization biased toward center."""
    circles = []
    center_x, center_y = 0.5, 0.5

    for i in range(26):
        angle = (2 * math.pi * i) / 26.0
        radius = 0.35 * ((i + 1) / 26.0)
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        x = max(0.05, min(0.95, x))
        y = max(0.05, min(0.95, y))
        circles.append([x, y, 0.0])

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

    # Initialize with multiple diverse patterns
    init_patterns = []

    # Pattern 1: Hexagonal
    init_patterns.append(create_hexagonal_init())

    # Pattern 2-5: Various grids
    init_patterns.append(create_grid_init(5, 6))
    init_patterns.append(create_grid_init(6, 5))
    init_patterns.append(create_grid_init(7, 4))

    # Pattern 6: Optimized grid
    init_patterns.append(create_optimized_grid_init())

    # Pattern 7: Corner-biased
    init_patterns.append(create_corner_biased_init())

    # Pattern 8: Spiral
    init_patterns.append(create_spiral_init())

    # Pattern 9: Random clustered
    init_patterns.append(create_random_clustered_init())

    # Pattern 10: Dense grid
    init_patterns.append(create_dense_grid_init())

    # Pattern 11: Uniform random
    init_patterns.append(create_uniform_random_init())

    # Pattern 12: Center-biased radial
    init_patterns.append(create_center_biased_init())

    # Optimize each pattern with aggressive refinement
    for pattern_idx, init_circles in enumerate(init_patterns):
        circles = refine_aggressive_multi_phase(init_circles, num_phases=8)

        # Validate solution
        if validate_solution(circles):
            total_radius = score_solution(circles)
            if total_radius > best_score:
                best_score = total_radius
                best_circles = circles

    # Aggressive perturbation loop to escape local optima
    if best_circles:
        for perturbation_iter in range(12):
            perturbation_amount = 0.035 * (1.0 - perturbation_iter / 12.0)
            perturbed = create_perturbed_init(best_circles, perturbation_amount)
            circles = refine_aggressive_multi_phase(perturbed, num_phases=7)

            if validate_solution(circles):
                total_radius = score_solution(circles)
                if total_radius > best_score:
                    best_score = total_radius
                    best_circles = circles

    # Additional refinement with ultra-fine tuning
    if best_circles:
        for ultra_iter in range(3):
            circles = [list(c) for c in best_circles]
            circles = optimize_radii_ultra_aggressive(circles, max_iterations=4000)
            circles = optimize_positions_fine(circles, max_opt_iterations=800, initial_scale=0.001)
            circles = optimize_positions_enhanced(circles, max_opt_iterations=300, initial_scale=0.0004)

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
