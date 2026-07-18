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

def optimize_radii(circles, max_iterations=2000):
    """Aggressively grow all radii to maximum."""
    circles = [list(c) for c in circles]

    for iteration in range(max_iterations):
        max_growth = 0.0
        for i in range(26):
            x, y, r = circles[i]
            new_r = get_max_radius(x, y, circles, i)
            growth = new_r - r
            max_growth = max(max_growth, growth)
            circles[i][2] = new_r

        if max_growth < 1e-13:
            break

    return circles

def optimize_positions(circles, max_opt_iterations=500, search_scale=0.003):
    """Optimize circle positions through local search."""
    circles = [list(c) for c in circles]

    for opt_iter in range(max_opt_iterations):
        improvement_found = False

        for i in range(26):
            x, y, r = circles[i]
            current_radius = r
            best_radius = current_radius
            best_config = (x, y, r)

            # Adaptive step size that decreases over time
            step_size = search_scale * (1.0 - opt_iter / max_opt_iterations)

            # Extended search: 7x7 neighborhood = 48 positions
            for dx_factor in range(-3, 4):
                for dy_factor in range(-3, 4):
                    if dx_factor == 0 and dy_factor == 0:
                        continue

                    nx = x + dx_factor * step_size
                    ny = y + dy_factor * step_size

                    if 0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0:
                        new_radius = get_max_radius(nx, ny, circles, i)

                        if new_radius > best_radius + 1e-11:
                            best_radius = new_radius
                            best_config = (nx, ny, new_radius)
                            improvement_found = True

            circles[i] = list(best_config)

        if not improvement_found:
            break

    return circles

def refine_aggressively(circles, num_phases=3):
    """Multi-phase aggressive refinement."""
    circles = [list(c) for c in circles]

    for phase in range(num_phases):
        # Radius growth phase
        circles = optimize_radii(circles, max_iterations=500 + phase * 200)

        # Position refinement with phase-dependent parameters
        search_scale = 0.004 * (1.0 - phase / (num_phases * 2))
        circles = optimize_positions(circles, max_opt_iterations=400 - phase * 50, search_scale=search_scale)

    # Final fine-tuning with very small steps
    circles = optimize_radii(circles, max_iterations=1000)

    return circles

def create_hexagonal_init(density_factor=1.0):
    """Create hexagonal-inspired packing initialization."""
    circles = []

    # Hexagonal packing parameters
    rows = 7
    cols = 5

    for row in range(rows):
        for col in range(cols):
            if len(circles) < 26:
                # Hexagonal offset for alternate rows
                x = (col + 0.5 + (0.25 if row % 2 == 1 else 0.0)) / (cols + 0.25)
                y = (row + 0.5) / (rows + 0.5)

                if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                    circles.append([x, y, 0.0])

    # Pad with random if needed
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

def create_perturbed_init(base_circles, perturbation=0.03):
    """Create a perturbed version of base circles."""
    circles = []
    for x, y, r in base_circles:
        nx = x + random.uniform(-perturbation, perturbation)
        ny = y + random.uniform(-perturbation, perturbation)
        nx = max(0.01, min(0.99, nx))
        ny = max(0.01, min(0.99, ny))
        circles.append([nx, ny, 0.0])
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

    # Initialize with multiple patterns
    init_patterns = []

    # Pattern 1: Hexagonal-optimized
    init_patterns.append(create_hexagonal_init())

    # Pattern 2: 6x5 grid
    init_patterns.append(create_grid_init(5, 6))

    # Pattern 3: 5x6 grid (transposed)
    init_patterns.append(create_grid_init(6, 5))

    # Pattern 4: 4x7 grid
    init_patterns.append(create_grid_init(7, 4))

    # Pattern 5: Perturbation of hexagonal
    hex_base = create_hexagonal_init()
    init_patterns.append(create_perturbed_init(hex_base, 0.02))

    # Optimize each pattern with aggressive refinement
    for pattern_idx, init_circles in enumerate(init_patterns):
        circles = refine_aggressively(init_circles, num_phases=4)

        # Validate solution
        if validate_solution(circles):
            total_radius = score_solution(circles)
            if total_radius > best_score:
                best_score = total_radius
                best_circles = circles

    # Try perturbations of the best solution to escape local optima
    if best_circles:
        for perturbation_iter in range(3):
            perturbed = create_perturbed_init(best_circles, 0.015 * (1.0 - perturbation_iter / 3.0))
            circles = refine_aggressively(perturbed, num_phases=3)

            if validate_solution(circles):
                total_radius = score_solution(circles)
                if total_radius > best_score:
                    best_score = total_radius
                    best_circles = circles

    # Final validation
    if best_circles and validate_solution(best_circles):
        print(best_circles)
    else:
        print([[0.5, 0.5, 0.0]] * 26)

if __name__ == "__main__":
    main()
