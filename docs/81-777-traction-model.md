# 81-777 traction model

## Sourced target

The public technical specification for the 81-775/776/777 family lists a
maximum acceleration of **1.3 m/s²**. The simulator profile therefore uses
1.3 m/s² as the low-speed, full-controller-notch calibration target.

This is a train-family figure. It is not an assertion that an individual
unpowered 81-777 trailer produces traction; the simulator's 81-777 profile
represents the complete eight-car train consist.

## Simulation approximation

A manufacturer traction-force, motor-current, or acceleration-versus-speed
curve was not available in the sources reviewed. The simulator therefore uses
a transparent provisional effort curve for full notch:

| Speed | Available traction effort |
| ---: | ---: |
| 0–30 km/h | 100% |
| 60 km/h | 75% |
| 90 km/h | 35% |

Values between the listed points are linearly interpolated. The four
controller notches are scaled to 25%, 50%, 75%, and 100% of the configured
1.3 m/s² maximum before the speed factor is applied.

These intermediate values are gameplay/physics approximations, not factory
data. They should be replaced if a manufacturer traction curve or measured
acceleration logs become available.

## Related braking calibration

The separate braking calibration retains the published 1.1 m/s² maximum
service deceleration. Its notch and speed curves are also documented as
approximations in the braking model documentation.
