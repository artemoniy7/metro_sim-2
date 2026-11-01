# 81-760/761 braking model

This note records which parts of the simulator braking model are grounded in the uploaded training material and which values remain game approximations.

## Source-derived behaviour

### Electrodynamic brake

The uploaded document «Электрическое оборудование 81-760/761» describes the KATP-2 asynchronous traction drive and states:

- the drive performs regenerative-rheostatic electric braking;
- there are three brake-current settings: Тормоз 1 / 2 / 3 = 40% / 65% / 100% of maximum motor current;
- the current setting is corrected for car loading;
- electric braking is available down to approximately 5 km/h;
- at maximum T3 braking with a fully loaded car, the current command begins reducing from 55 km/h, reaching 260 A at 20 km/h;
- regenerative braking returns energy to the contact network when it can accept it; otherwise the drive uses the braking chopper and resistor (rheostatic braking);
- the document gives maximum-service electric-braking stopping-distance values of 150 m from 60 km/h and 260 m from 80 km/h.

core/electrodynamic_brake.py implements the three documented current fractions, the 55-to-20 km/h reduction, the 5 km/h cut-out, and the regenerative/rheostatic operating mode. The simulator's conversion from current fraction to deceleration is calibrated at 1.0 m/s² for T3; this is a game calibration against the cited stopping-distance envelope, not a published factory torque/current curve.

The source describes the reduction down to 260 A at 20 km/h but does not give the complete low-speed current curve. The 20-to-5 km/h taper is therefore an explicit interpolation in the game model.

### Pneumatic and friction brake

The uploaded document «Пневматическое оборудование 81-760/761» describes:

- compressor cut-in at approximately 6.5 atm and cut-out at 8.0 atm;
- nominal charged brake-pipe pressure 5.2 ± 0.1 atm;
- the БУФТ-076 friction-brake control unit, pressure relays and load-dependent automatic regulator (АРП);
- four friction-brake cylinders per car / two bogie brake circuits;
- spring-applied parking brake released by pressure from the main reservoir;
- anti-slide valves ВПУ1/ВПУ2, which vent the corresponding pressure-relay control chambers to release one or both bogies during detected wheel slide.

The implementation keeps the main reservoir (НМ), brake pipe (ТМ), brake cylinders (ТЦ), door circuit, air suspension and spring parking-brake circuit separate. The normal service brake is electrodynamic; pneumatic friction braking is blended in at low speed and takes over if the electric brake is unavailable. Emergency braking uses the pneumatic emergency command. The parking brake is spring-applied and pressure-released. The anti-slide interface can release an individual bogie circuit.

The training material does not provide all per-frame filling/exhaust flow coefficients or a complete БУФТ transfer curve. Those timing coefficients and the pressure-to-deceleration conversion remain simulation approximations. Automatic wheel-slide detection is also limited by the current game physics: the bogie release interface is present, but the simulator does not yet model individual wheel rotational speeds or a complete adhesion controller.

### Train control and safety

The uploaded «Управление электропоездами моделей 81-760/761» describes automatic replacement of ineffective/exhausted electric braking with pneumatic friction braking, the separate holding-brake function near zero speed, and emergency braking through the safety loop. The game model represents these as service-brake fallback, low-speed hold pressure, and a separate emergency pneumatic command. It does not reproduce the complete certified БКВУ/БКПУ/АРС safety hardware or its diagnostic logic.

## Model boundaries

This is a simulation model for the game, not a maintenance, training, or safety-control implementation. Values explicitly marked as approximations must be calibrated by running the simulator against its desired stopping distances and by checking the complete source manuals. In particular, the manual's per-car stopping-distance table is a reference envelope; it is not sufficient by itself to reconstruct every train-level brake force, load state, adhesion condition, or control-system delay.