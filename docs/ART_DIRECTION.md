# Art direction

The goal is the look of *Morrowind* (vanilla and lightly modded OpenMW): simple, chunky geometry carried by painterly textures and, above all, by weather. Keep that balance when extending the world.

## Atmosphere first

- The fog colour **is** the sky's horizon colour. Distant land dissolves into it; never let far geometry read as a crisp cut-out.
- Every weather has four moods (sunrise, day, sunset, night). Change colours in the tables in `scripts/world/weather.gd`, not in materials.
- Sunsets are warm and saturated, nights are dark blue with stars and two moons, rain and storms crush the view distance, ashstorms turn everything rust-brown.
- Practical lights (fire baskets, lamp standards, lanterns, lit windows) are warm amber and carry the night scenes.

## Surfaces

- Textures are 256–512 px, generated in `tools/build_textures.py`: low-frequency colour mottling, baked relief shading, muted earthy palettes. Avoid photographic sharpness and glossy PBR — materials are matte Lambert with specular off (only the sword blade shines).
- Texel density is set per material in `tools/materials.json` (`scale` = metres per repeat). Keep new models on the same scale so surfaces match.
- Ground darkening at the base of buildings comes from vertex colours (`ground_ao` in `tools/meshlib.py`).

## Architecture kits

- **Imperial** (image 6): fieldstone foundation, olive plaster, dark timber framing, hexagonal bay windows with leaded diamond glass, steep shingle roofs with dormers, protruding purlins and rafter tails.
- **Redoran** (image 1): sweeping banded shell vaults with heavy rolled rims, stepped pointed portals, bell domes with a capped neck, spikes and tusks.
- **Velothi/Dunmer common**: smooth adobe domes, arched vestibules, round windows.
- **Temple** (image 5): grey-green ashlar, lancet windows with green bullseye glass, two-tier copper pagoda roofs with upturned eaves, lattice gate.
- **Fortress** (image 3): seen only as a hazy silhouette across the water.

## Landscape

- Splat layers: grass, dirt, rock (triplanar on slopes), mud, ash, sand, cobble and gravel road. Transitions use height-aware blending for an organic edge.
- Rocks and cliff pieces sit on steep slopes; trees and flora are scattered by biome with clearance from roads and buildings.
- Each district has a recognisable landmark at the end of its road: the temple, the shell hall, the mine portal, the lighthouse.
