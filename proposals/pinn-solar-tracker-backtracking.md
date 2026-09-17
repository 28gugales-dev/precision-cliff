# Physics-Informed Neural Network for Per-Row Backtracking of Single-Axis Solar Trackers on Uneven Terrain

## A. Rationale

Most large solar farms use single-axis trackers. Each row of panels turns during the day to follow the sun. Early in the morning and late in the afternoon the sun sits low, so one row can throw a shadow on the row next to it. To avoid that, trackers use a trick called backtracking. They tilt the rows back toward flat until the shadows clear, then go back to following the sun.

The catch is that the normal backtracking formula assumes the ground is flat. Real sites are not. On rolling land, one row might sit a meter higher than its neighbor, and the slope between rows changes as you move across the field. When the controller uses the flat-ground formula anyway, it gets the angle wrong. Sometimes the rows still shade each other. Other times they tilt back more than they need to and miss sunlight. Either way the farm loses energy.

The loss per row is small, but across thousands of rows and a whole year it adds up. What makes this interesting to me is that it looks fixable without new hardware. The terrain does not move. If a controller could learn the shape of the site and pick a better angle for each row, the fix would be pure software.

## B. Research Question

Can a physics-informed neural network (PINN) choose per-row tracker angles that produce more yearly energy on uneven terrain than standard backtracking does?

## C. Hypothesis

I expect the PINN to raise simulated annual energy by somewhere between 1 and 3 percent over standard backtracking on sites where slope varies by more than 5 percent. On flat sites I expect the gain to be close to zero, because standard backtracking is already about right there.

## D. Engineering Goals

1. Beat standard backtracking on annual energy yield.
2. Match, or come close to, the slope-aware analytical method from NREL.
3. Run fast enough to sit inside a real controller. My target is under one second per time step.

## E. Procedures

1. Pick 5 to 10 test sites with a mix of terrain: some flat, some gently sloped, some rolling. Download elevation data (a DEM) for each site from USGS.
2. Download one year of irradiance and weather data for each site from the NREL National Solar Radiation Database.
3. Lay out a simulated tracker field on each site. Set the row spacing and row length, and take each row's axis height from the elevation data.
4. Build three baselines in pvlib: true tracking with no backtracking, standard flat-ground backtracking, and slope-aware backtracking.
5. Write a shading model. It takes the sun position plus each row's height and tilt, and works out how much of each row its neighbor is shading.
6. Train the PINN. The inputs are sun position, row heights, the slopes to neighboring rows, and irradiance. The output is one angle per row. The loss is the negative of the energy produced, plus a physics penalty whenever the chosen angles cause shading or go past the tracker's mechanical limits.
7. Train on some of the sites and hold the rest back. Test only on sites the model has never seen, so I know it learned something general instead of memorizing the training sites.
8. Run every method for a full year on each test site and record the energy.

## F. Risk and Safety

Everything here is computer simulation on public datasets. There are no human subjects, no animals, no chemicals, and no physical devices. I do not see any notable risks.

## G. Data Analysis

For each site and each method I will record annual energy in kWh. From that I will report the percent gain of each method over standard backtracking.

I also want to see where the method helps and where it does not, so I will plot gain against a terrain roughness measure for each site. If the hypothesis holds, the gain should grow as the terrain gets rougher.

To check that the gains are real and not noise, I will run a paired t-test across sites and across days. I will also report the shading loss percent for each method and the compute time per step, since the speed goal matters as much as the energy goal.

## H. Bibliography

1. Anderson, K. and Mikofski, M. "Slope-Aware Backtracking for Single-Axis Trackers." NREL Technical Report, 2020.
2. Holmgren, W., Hansen, C., and Mikofski, M. "pvlib python: a python package for modeling solar energy systems." Journal of Open Source Software, 2018.
3. Raissi, M., Perdikaris, P., and Karniadakis, G. "Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations." Journal of Computational Physics, 2019.
4. Sengupta, M. et al. "The National Solar Radiation Data Base (NSRDB)." Renewable and Sustainable Energy Reviews, 2018.
5. Lorenzo, E., Narvarte, L., and Muñoz, J. "Tracking and back-tracking." Progress in Photovoltaics: Research and Applications, 2011.
