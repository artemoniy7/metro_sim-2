# 81-777 low-speed braking and wheel-squeal tuning

## Braking

The service-brake ceiling remains **1.1 m/s²**, the published maximum
deceleration used by the simulator profile. This change does not claim a
higher factory braking force.

The previous electrodynamic-brake approximation began fading below 15 km/h
and reached zero at 5 km/h. The revised curve keeps full configured ED effort
down to 8 km/h, then fades it to zero at 2 km/h. Pneumatic replacement now
begins at 18 km/h instead of 10 km/h, giving the pneumatic system more time
to build pressure before ED effort falls away. The existing combined
deceleration cap remains 1.1 m/s².

These crossover and fade speeds are simulation tuning values, not published
manufacturer thresholds. The intention is to avoid the perceived loss of
braking near the end of a stop while preserving the sourced maximum.

## Wheel squeal

Wheel squeal remains linked to a braking command. It rises between 15 and
20 km/h, then gradually fades from 45 km/h to silence at 70 km/h. Its
base/maximum mix levels are reduced from 0.10/0.22 to 0.06/0.16.

The high-speed cutoff and mix levels are audio/gameplay tuning, not a claim
that real wheel/rail squeal is physically impossible above 70 km/h.
