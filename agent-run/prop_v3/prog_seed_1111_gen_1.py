import math
import random

random.seed(1111)

def dist(c1, c2):
    """Euclidean distance between circle centers."""
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

def in_bounds(x, y, r):
    """Check if circle is strictly inside [0,1]x[0,1]."""
    return x - r >= -1e-10 and x + r <= 1 + 1e-10 and y - r >= -1e-10 and y + r <= 1 + 1e-10

def get_max_radius(x, y, circles, idx):
    """Get maximum radius for a circle at (x,y) given other circles."""
    # Constrained by bounds
    r_max = min(x, 1 - x, y, 1 - y)

    # Constrained by other circles (tangency is OK)
    for j in range(len(circles)):
        if j != idx:
            d = dist([x, y, 0], circles[j])
            r_max = min(r_max, d - circles[j][2])

    return max(0, r_max)

# ==============================================================================
# STEP 1: Initial placement using hexagonal packing pattern
# ==============================================================================
circles = []
n_cols = 6
hex_spacing_x = 1.0 / (n_cols - 1)
hex_spacing_y = hex_spacing_x * math.sqrt(3) / 2

row = 0
while len(circles) < 26:
    y = row * hex_spacing_y
    if y > 1.0 + 1e-9:
        break

    # Offset every other row for hexagonal packing
    x_offset = hex_spacing_x / 2 if row % 2 == 1 else 0

    col = 0
    while len(circles) < 26:
        x = col * hex_spacing_x + x_offset
        if x > 1.0 + 1e-9:
            break

        # Clip to [0,1]
        x = min(x, 1.0)
        y = min(y, 1.0)

        circles.append([x, y, 0.02])
        col += 1

    row += 1

# Ensure we have exactly 26 circles
circles = circles[:26]

# ==============================================================================
# STEP 2: Iteratively grow radii while maintaining non-overlap and bounds
# ==============================================================================
max_iterations = 2000
tolerance = 1e-11

for iteration in range(max_iterations):
    old_radii = [c[2] for c in circles]

    # For each circle, maximize its radius given current positions
    for i in range(26):
        max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
        circles[i][2] = max(0, min(max_r, circles[i][2] + 0.001))  # gradual growth

    # Check for convergence
    new_radii = [c[2] for c in circles]
    max_delta = max(abs(new_radii[i] - old_radii[i]) for i in range(26)) if new_radii else 0

    if max_delta < tolerance:
        break

# ==============================================================================
# STEP 3: Fine-tune by exactly maximizing each radius
# ==============================================================================
for _ in range(200):
    changed = False
    for i in range(26):
        max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
        if max_r > circles[i][2] + 1e-12:
            circles[i][2] = max_r
            changed = True

    if not changed:
        break

# ==============================================================================
# STEP 4: Local position adjustment (shift circles slightly to create space)
# ==============================================================================
for shift_iter in range(100):
    shifted = False
    for i in range(26):
        x, y, r = circles[i]

        # Try small displacements in 8 directions
        best_r = r
        best_x, best_y = x, y

        for dx in [-0.005, 0, 0.005]:
            for dy in [-0.005, 0, 0.005]:
                if dx == 0 and dy == 0:
                    continue

                nx = x + dx
                ny = y + dy

                # Check if within bounds at least with zero radius
                if 0 <= nx <= 1 and 0 <= ny <= 1:
                    nr = get_max_radius(nx, ny, circles, i)
                    if nr > best_r + 1e-12:
                        best_r = nr
                        best_x = nx
                        best_y = ny
                        shifted = True

        circles[i] = [best_x, best_y, best_r]

    if not shifted:
        break

# ==============================================================================
# STEP 5: Final radius maximization after position adjustment
# ==============================================================================
for _ in range(300):
    changed = False
    for i in range(26):
        max_r = get_max_radius(circles[i][0], circles[i][1], circles, i)
        if max_r > circles[i][2] + 1e-12:
            circles[i][2] = max_r
            changed = True

    if not changed:
        break

# ==============================================================================
# STEP 6: Validation and cleanup
# ==============================================================================
for i in range(26):
    x, y, r = circles[i]

    # Ensure within bounds
    r = min(r, x, 1 - x, y, 1 - y)
    circles[i][2] = max(0, r)

    # Clamp position to [0,1]
    circles[i][0] = max(0, min(1, x))
    circles[i][1] = max(0, min(1, y))

# Verify no overlaps
for i in range(26):
    x, y, r = circles[i]
    assert in_bounds(x, y, r), f"Circle {i} out of bounds"

    for j in range(i + 1, 26):
        x2, y2, r2 = circles[j]
        d = dist(circles[i], circles[j])
        assert d >= circles[i][2] + circles[j][2] - 1e-9, f"Circles {i} and {j} overlap"

print(circles)
