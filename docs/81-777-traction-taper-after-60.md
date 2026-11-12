# 81-777 traction taper above 60 km/h

The simulation keeps the configured full-notch launch acceleration of 1.3 m/s²
through approximately 60 km/h. Above 60 km/h, traction effort tapers linearly:

| Speed | Traction effort factor | Full-notch acceleration |
|---:|---:|---:|
| 0 km/h | 100% | 1.300 m/s² |
| 30 km/h | 100% | 1.300 m/s² |
| 60 km/h | 100% | 1.300 m/s² |
| 75 km/h | 67.5% | 0.878 m/s² |
| 90 km/h | 35% | 0.455 m/s² |

Values between points are linearly interpolated. The 1.3 m/s² low-speed maximum
is the published family figure used for calibration; the taper above 60 km/h
is a simulation approximation, not a verified factory traction curve.
