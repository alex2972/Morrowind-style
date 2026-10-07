# Player head revision

The reference guided the bald, angular head, distinct chin, tapered jaw and leaner neck.

## Delivered assets

- Game mesh: `assets/models/player_body.glb` (4,822 triangles).
- Painted atlas: `assets/textures/char_body.png` (1024 x 1024).
- Game scene: `scenes/props/player_body.tscn`.
- Editable Blender model with packed texture: `docs/character_head/after/player_body.blend`.
- Renders: `after/front.png`, `after/profile.png`, `after/threequarter.png`, `after/body.png`.
- Before/after contact sheet: `comparison.png`.

The chin is longer and projects forward, mandibular corners taper inward, cheek hollows and brow projection are reduced, and the ears are smaller. The neck circumference and width are reduced; its join sits lower and has an in-plane relaxation pass. The eye sockets have lighter baked shadows and separately painted angular eyebrows. Facial planar reduction is less aggressive so the lips and jaw keep more shape.

Body and limb target settings and pose are retained. Rebuilding the shared mesh regenerates its decimation and UV atlas. The original GLB, texture, player scene and generator are preserved in `before/`.

## Rebuild only this character

Run from the project root in PowerShell:

```powershell
& '.\Blender\blender.exe' --background --python-exit-code 1 --python tools\build_character.py -- --blend docs/character_head/after/player_body.blend
& '.\Blender\blender.exe' --background --python-exit-code 1 --python tools\rig_character.py
& 'Z:\godot\Godot_v4.7.1-stable_win64_console.exe' --headless --editor --path . --import
& 'Z:\godot\Godot_v4.7.1-stable_win64_console.exe' --headless --path . --script res://tools/refresh_character.gd
& '.\Blender\blender.exe' --background --python-exit-code 1 --python tools\preview_character_head.py -- docs/character_head/after
```

MPFB is installed as a Blender user extension, so do not add `--factory-startup`. The character refresh rebuilds the prop used by the existing world. No world regeneration is needed.

The front and profile images use matching orthographic cameras and lighting. They are Blender renders, not in-game screenshots. This directory is excluded from Godot import via `.gdignore`.
