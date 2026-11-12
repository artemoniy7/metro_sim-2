# 81-777 early acceleration taper

The 81-777 simulation keeps the configured low-speed launch maximum at 1.3 m/s².
The previous approximation held full traction effort through 30 km/h. This
revision keeps full effort at standstill, then tapers it progressively:

| Speed | Traction effort factor | Full-notch acceleration |
|---:|---:|---:|
| 0 km/h | 100% | 1.300 m/s² |
| 10 km/h | 92% | 1.196 m/s² |
| 30 km/h | 72% | 0.936 m/s² |
| 60 km/h | 48% | 0.624 m/s² |
| 90 km/h | 25% | 0.325 m/s² |

Values between points are linearly interpolated. The 1.3 m/s² launch target is
the published family maximum used for calibration; the intermediate
speed-dependent factors are simulation tuning, not a manufacturer traction
curve.
