# Metro Sim

A small Python/Pygame metro driving simulator. The playable train is the 81-760 «Ока», using the sprites in `assets/trains/81-760/`.

## Run
```bash
python -m pip install -r requirements.txt
python main.py
```

## Controls
- **W / Up** — traction
- **S / Down** — service brake
- **Space** — emergency brake
- **Q / E** — move to the adjacent track at a crossover (when the switch is free)
- **Esc** — quit

## Scale and route
- World distances are in metres.
- Stations on the test route are spaced 1,000 m apart.
- The leading 81-760 cab is 20 m long; each following car is 19 m.
- The camera uses 50% zoom (twice as far out as the previous view) and follows the leading cab.
- Train textures are loaded from `assets/trains/81-760/81-760-loco.png` and `assets/trains/81-760/81-760-car.png`.
- The test scene includes three parallel, same-level tracks. Their screen-space spacing is not an elevation difference.
- Crossovers are placed along the route. Q/E requests a lane change only near a crossover and only when its conflict zone is clear.
- A train reserves both connected tracks until the rear of the entire consist has cleared the switch. Trains on separate tracks do not consume each other's ALS-ARS blocks.
- The line 9 layout is configured in `data/tracks/line_9.json`; depot yard tracks are described in `data/depots/vladykino.json`.
