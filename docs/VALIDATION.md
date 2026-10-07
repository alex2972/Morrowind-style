# Validation

Validated on 2026-10-03 with Godot 4.7.1 (Forward+, Vulkan, Jolt Physics) on an NVIDIA RTX 3060. Assets were generated with Python 3.10 (numpy, Pillow) and Blender 5.2.1 in background mode (the player model with the MPFB 2.0.17 extension).

`tools/verify_world.gd` (headless, 60 fixed FPS) passed all 17 checks:

- Player spawns standing on the harbour pier.
- Continuous walk from the pier onto the quay, along the main street to the plaza.
- Climbing the temple stairs.
- Continuous walk along the north road to the mine and through the tunnel to the cavern.
- Interior lighting takes over inside the mine, and the region reports the mine.
- Continuous walk along the east road up onto the Shell Ward plateau.
- Continuous walk along the west road to the marsh.
- Swimming in deep water.
- All seven weather types; waiting one hour; the pause menu; returning to the harbour.
- Tab shows the player model with the camera pulled about 2.9 m back, and first person hides it again.

The run ended with `VERIFICATION_FAILURES 0`. A normal (windowed) run of 900 frames and a headless editor load produced no script or resource errors.

The player model was compared view by view (front, side, back, face) against the reference turnaround, with silhouette overlays at equal height, and checked in game at noon and dusk.

Visual review: the screenshots in `docs/previews/` were captured from the running game with the capture mode in `scripts/world/world.gd` and compared against the reference images. Frame rate during capture at 1600×900 was roughly 65–125 FPS (planar water reflection included); the first frames after launch are slower while shaders compile.

This is automated route checking plus visual review, not an exhaustive manual playthrough or a benchmark on other hardware.
