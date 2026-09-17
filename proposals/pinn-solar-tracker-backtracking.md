# Physics-Informed Neural Network for Per-Row Backtracking of Single-Axis Solar Trackers on Uneven Terrain

Adult sponsor: Shailesh Gugale (parent)

Start date: September 16, 2026

## A. Rationale

Single-axis trackers turn rows of solar panels through the day to follow the sun. When the sun is low, one row can shade the row next to it, so trackers use backtracking: they tilt the rows back toward flat until the shadows clear, then keep following the sun.

The standard backtracking formula assumes flat ground. On rolling terrain each row sits at its own height and slope, so the formula gets the angle wrong. Sometimes the rows still shade each other. Sometimes they tilt back further than they need to and miss sunlight. Both cost energy.

That loss looks recoverable. The terrain does not move, so a controller that learned the shape of the site could pick a better angle for each row without any new hardware. NREL has shown that better backtracking on rolling terrain can raise energy output by 1 to 2 percent (Anderson, Jensen, and Riley, 2026), so the gain is real and worth chasing.

## B. Research question

Can a physics-informed neural network (PINN) choose per-row tracker angles that produce more yearly energy on uneven terrain than standard backtracking, and come close to the best angles a full optimizer can find, while running fast enough for a real controller?

## C. Hypothesis

I expect the PINN to raise simulated annual energy by 1 to 3 percent over standard backtracking on sites where slope variation is above 5 percent. On flat sites the gain should be close to zero, since the flat-ground formula is already right there. Against the strongest baseline, a per-step optimizer that searches all row angles directly, I expect the PINN to land within 0.5 percent of its energy while running at least 100 times faster per step.

## D. Engineering goals

1. Beat standard backtracking on annual energy yield.
2. Match slope-aware analytical backtracking, or come close to it.
3. Come within 0.5 percent of the per-step optimizer's energy.
4. Run fast enough for real-time control, under one second per time step for a field of at least 50 rows.

## E. Why a PINN instead of a plain optimizer

A fair question is why not just run an optimizer at every time step. That is in fact one of my baselines, and it sets the ceiling for energy. It has two problems as a controller. First, the angles of neighboring rows are coupled through shading, so the problem is nonlinear and has to be solved again for every row, every time step, at every site. On a big field that can take longer than the control interval. Second, the answer for one site tells you nothing about the next site, so nothing is reused.

NREL's linear programming method (Anderson, Jensen, and Riley, 2026) is a smart way around the speed problem. It turns shade avoidance into a linear problem, which solves fast. But it works by limiting the shaded fraction rather than by maximizing energy directly, so it can leave a little energy on the table when a small amount of shade would be worth taking for more direct sunlight.

A neural network amortizes the optimization (Amos, 2023). The expensive work happens once, during training. After that, one forward pass gives the angles for every row, and the same network can be applied to a site it has never seen. The physics part of the PINN is what makes this safe: the loss includes the shading geometry and the angle limits, so the network cannot learn angles that break the physics, and it can train without needing labeled answers from an optimizer. If the PINN cannot beat the linear program on energy, then its value has to show up as speed or generality, and if it shows neither, the hypothesis is rejected.

## F. Procedures

1. Pick 5 to 10 test sites with different terrain: flat, gentle, and rolling. Download DEM elevation data for each from USGS.
2. Download one year of irradiance and weather data for each site from the NREL NSRDB.
3. Lay out a simulated tracker field on each site, with row spacing, row length, and each row's axis height taken from the DEM.
4. Write a shading model that takes the sun position and each row's height and tilt, and works out how much shade falls from one row onto the next. I will check it against the closed-form shaded fraction equations for rolling terrain (Anderson and Jensen, 2024).
5. Build four baselines in pvlib: true tracking with no backtracking, standard flat backtracking, slope-aware backtracking (Anderson and Mikofski, 2020), and NREL's linear programming backtracking (Anderson, Jensen, and Riley, 2026).
6. Build the upper bound: a per-step nonlinear optimizer (SciPy) that searches all row angles at once to maximize energy from the shading model directly. This is slow but sets the ceiling for what any method can reach.
7. Train the PINN. Inputs are sun position, row heights, neighbor slopes, and irradiance. The output is one angle per row. The loss is negative energy plus a physics penalty for shading and for angles past the tracker limits.
8. Train on some sites and test on sites the model never saw.
9. Run every method for the full year on each test site and record the energy and the compute time per step.

## G. Materials

- A laptop with Python 3.11 or newer.
- pvlib for solar position, irradiance transposition, and the backtracking baselines.
- PyTorch for the PINN.
- NumPy, SciPy, pandas, and matplotlib for the shading model, the optimizer, data handling, and plots.
- USGS 3D Elevation Program (3DEP) DEM tiles, downloaded free from The National Map.
- NREL NSRDB hourly irradiance and weather data, downloaded with a free API key.
- A free GPU session on Google Colab or Kaggle for training runs.
- Git and GitHub for code and version history.

No physical equipment, lab space, or purchases are needed.

## H. Risk and safety

All of the work is computer simulation on public datasets. There are no human subjects, animals, hazardous chemicals, or devices, and I do not see any notable risks.

## I. Data analysis

For each site and method I will record annual energy in kWh and report the percent gain over standard backtracking. I will also report each method's gap to the per-step optimizer, since that shows how much energy is still being missed. I will plot gain against terrain roughness to see where the method helps most. To check whether the gains are real, I will run a paired t-test across sites and days. I will also report the shading loss percent and the compute time per step for every method, so the speed goal is tested with the same care as the energy goal.

## J. Acknowledgements and AI use

I thank my father, Shailesh Gugale, for sponsoring this project and reviewing the plan.

I used an AI assistant to help edit the wording of this proposal and to check the reference list. I may also use it to help debug code. The research question, the experimental design, the code, the analysis, and the conclusions are my own work, and any AI use in the final report will be stated there too.

## K. Bibliography

1. Anderson, K. and Mikofski, M. "Slope-Aware Backtracking for Single-Axis Trackers." NREL Technical Report NREL/TP-5K00-76626, 2020. https://www.nrel.gov/docs/fy20osti/76626.pdf
2. Anderson, K. S. and Jensen, A. R. "Shaded fraction and backtracking in single-axis trackers on rolling terrain." Journal of Renewable and Sustainable Energy, 16(2), 023504, 2024. https://doi.org/10.1063/5.0202220
3. Anderson, K. S., Jensen, A. R., and Riley, D. M. "A Linear Programming Approach to Backtracking for Single-Axis Trackers on Rolling Terrain." IEEE Journal of Photovoltaics, 16(2), 2026. https://doi.org/10.1109/JPHOTOV.2025.3645781
4. Amos, B. "Tutorial on Amortized Optimization." Foundations and Trends in Machine Learning, 16(5), 592 to 732, 2023. https://doi.org/10.1561/2200000102
5. Holmgren, W. F., Hansen, C. W., and Mikofski, M. A. "pvlib python: a python package for modeling solar energy systems." Journal of Open Source Software, 3(29), 884, 2018. https://doi.org/10.21105/joss.00884
6. Lorenzo, E., Narvarte, L., and Muñoz, J. "Tracking and back-tracking." Progress in Photovoltaics: Research and Applications, 19(6), 747 to 753, 2011. https://doi.org/10.1002/pip.1085
7. Raissi, M., Perdikaris, P., and Karniadakis, G. E. "Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations." Journal of Computational Physics, 378, 686 to 707, 2019. https://doi.org/10.1016/j.jcp.2018.10.045
8. Sengupta, M., Xie, Y., Lopez, A., Habte, A., Maclaurin, G., and Shelby, J. "The National Solar Radiation Data Base (NSRDB)." Renewable and Sustainable Energy Reviews, 89, 51 to 60, 2018. https://doi.org/10.1016/j.rser.2018.03.003
