# 81-777 «Москва-2020»: braking model

## Publicly supported characteristics

The published technical summary for the 81-775/776/777 family lists:

- design speed: 90 km/h;
- maximum acceleration: 1.3 m/s²;
- deceleration: 1.1 m/s²;
- asynchronous traction motors.

Source: [Encyclopedia of Our Transport — 81-775/776/777](https://wiki.nashtransport.ru/wiki/Вагоны_метрополитена_81-775/776/777).

The brake-system manufacturer describes the 81-775/776/777 system as a combination of:
- multi-stage electropneumatic braking;
- an autonomous automatic pneumatic brake;
- automatic pneumatic replacement of reduced or failed electrodynamic braking;
- load-dependent brake regulation;
- a separate emergency pneumatic control path.

Source: [MTZ Transmash — brake control system for 81-775/776/777](https://www.mtz-transmash.ru/news/2021/01/26/sistema_upravlenija_tormozami_dlja_vagonov_metropolitena_modelejj_81775776777_moskva2020/).

## Implemented simulation behaviour

- The maximum combined service-brake deceleration is capped at 1.1 m/s².
- Electrodynamic braking is enabled and has three proportional controller steps.
- The electric-brake contribution fades between 15 and 5 km/h.
- Pneumatic braking begins taking over below 10 km/h; the existing pneumatic subsystem remains a normalized game model, not a representation of factory pressure values.
- If the electric brake is unavailable, the existing pneumatic fallback is used.
- If regenerative energy cannot be accepted, the electric brake reports rheostatic mode.

## Explicit approximations

The public sources above do not provide the complete factory current/torque curve, per-notch deceleration curve, ED-to-pneumatic crossover speed, or pneumatic filling/exhaust timing. Therefore:

- the linear 1/3, 2/3, 1.0 notch scaling;
- the 15-to-5 km/h electric-brake fade;
- the 10 km/h pneumatic handover point;
- the normalized pneumatic pressure dynamics;

are simulation calibrations, not manufacturer specifications.

The 1.1 m/s² figure is the sourced maximum deceleration target. The code also uses it as a conservative cap for the combined service/emergency calculation because a separate emergency-deceleration value was not found in the public material.

This model is intended for gameplay realism, not for real train operation, maintenance, or safety engineering.
