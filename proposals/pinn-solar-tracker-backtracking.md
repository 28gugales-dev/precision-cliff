# Physics-Informed Neural Network for Per-Row Backtracking of Single-Axis Solar Trackers on Uneven Terrain

Teacher sponsor: Lidan Zhou

Start date: September 16, 2026

## A. Rationale

Single-axis trackers turn rows of solar panels through the day to follow the sun. When the sun is low, one row can shade the row next to it, so trackers use backtracking: they tilt the rows back toward flat until the shadows clear, then keep following the sun.

The standard backtracking formula assumes flat ground. On rolling terrain each row sits at its own height and slope, so the formula gets the angle wrong. Sometimes the rows still shade each other. Sometimes they tilt back further than they need to and miss sunlight. Both cost energy.

That loss looks recoverable. The terrain does not move, so a controller that learned the shape of the site could pick a better angle for each row without any new hardware.

## B. Research question

Can a physics-informed neural network (PINN) choose per-row tracker angles that produce more yearly energy on uneven terrain than standard backtracking does?

## C. Hypothesis

I expect the PINN to raise simulated annual energy by 1 to 3 percent over standard backtracking on sites where slope variation is above 5 percent. On flat sites the gain should be close to zero, since the flat-ground formula is already right there.

## D. Engineering goals

1. Beat standard backtracking on annual energy yield.
2. Match slope-aware analytical backtracking, or come close to it.
3. Run fast enough for real-time control, under one second per time step.

## E. Procedures

1. Pick 5 to 10 test sites with different terrain: flat, gentle, and rolling. Download DEM elevation data for each from USGS.
2. Download one year of irradiance and weather data for each site from the NREL NSRDB.
3. Lay out a simulated tracker field on each site, with row spacing, row length, and each row's axis height taken from the DEM.
4. Build three baselines in pvlib: true tracking with no backtracking, standard flat backtracking, and slope-aware backtracking.
5. Write a shading model that takes the sun position and each row's height and tilt, and works out how much shade falls from one row onto the next.
6. Train the PINN. Inputs are sun position, row heights, neighbor slopes, and irradiance. The output is one angle per row. The loss is negative energy plus a physics penalty for shading and for angles past the tracker limits.
7. Train on some sites and test on sites the model never saw.
8. Run every method for the full year on each test site and record the energy.

## F. Risk and safety

All of the work is computer simulation on public datasets. There are no human subjects, animals, hazardous chemicals, or devices, and I do not see any notable risks.

## G. Data analysis

For each site and method I will record annual energy in kWh and report the percent gain over standard backtracking. I will plot gain against terrain roughness to see where the method helps most. To check whether the gains are real, I will run a paired t-test across sites and days. I will also report the shading loss percent and the compute time per step.

## H. Bibliography

1. Anderson and Mikofski, "Slope-Aware Backtracking for Single-Axis Trackers," NREL, 2020.
2. Holmgren, Hansen, Mikofski, "pvlib python," JOSS, 2018.
3. Raissi, Perdikaris, Karniadakis, "Physics-Informed Neural Networks," J. Comp. Physics, 2019.
4. Sengupta et al., "The National Solar Radiation Data Base," 2018.
5. Lorenzo, Narvarte, Muñoz, "Tracking and back-tracking," Progress in Photovoltaics, 2011.
