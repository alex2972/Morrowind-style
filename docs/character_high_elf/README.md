# Male High Elf - first race preset

This is an original low-poly variant of the existing MakeHuman-derived male character. The supplied screenshot guides its long face, sharp cheeks, pointed ears, gold skin and a strong jaw. The character is bald; no screenshot pixels are used in game textures.

## Delivered

- `assets/models/player_high_elf_male.glb`: bald skinned body, with the existing animation set.
- `assets/textures/char_high_elf_male.png`: 1024-square painted race atlas using the base UVs; amber skin and gold irises.
- `scenes/props/player_high_elf_male.tscn`: game scene with the player render layer and matching materials.
- `docs/character_high_elf/high_elf_male.blend`: editable model, packed textures, shared rig and animation actions.
- `tools/high_elf_male.json`: adjustable shape/colour settings.
- `tools/build_race_character.py`: repeatable post-process of the finished base; does not rebuild a separate skeleton or modify the source character.

Male High Elf selection uses the new scene in the lobby, world player, other actors, and portrait. Female High Elves and other races retain their existing models. No female or other race sculpt is included in this first review pass.

## Rig and proportions

The 53 bones, their rest matrices, body weights, body topology, UVs and 73 animation clips are retained. The body is subtly slimmer; the existing runtime High Elf scale (1.06) supplies height once, so the animation skeleton and foot placement remain compatible. Changing limb lengths would require an additional proportion-aware animation step, not merely sharing bone names.

The high elf is bald. Its jaw now tapers diagonally to a compact, pointed chin rather than extending into a broad block. The neck is slimmer with a tucked throat; the forehead recedes above a pronounced, angled brow ridge. The original straight eyebrows are removed and replaced with lower, feathered, rising brows, with restrained forehead and socket shading. Ears are sculpted from the original head topology. Hair and runtime face sliders are not implemented. Earlier iterations are archived under `before_jaw_revision/` and `before_reference_revision/`.

## Rebuild this race only

Run in PowerShell from the project root:

```powershell
& './Blender/blender.exe' --background --python-exit-code 1 --python tools/build_race_character.py
& 'Z:/godot/Godot_v4.7.1-stable_win64_console.exe' --headless --editor --path . --import
& 'Z:/godot/Godot_v4.7.1-stable_win64_console.exe' --headless --path . --script res://tools/refresh_character.gd -- player_high_elf_male
& 'Z:/godot/Godot_v4.7.1-stable_win64_console.exe' --headless --path . --script res://tools/verify_race_character.gd
& './Blender/blender.exe' --background --python-exit-code 1 --python tools/preview_race_character.py
& './Blender/blender.exe' --background --python-exit-code 1 --python tools/preview_race_character.py -- --base
& './Blender/blender.exe' --background --python-exit-code 1 --python tools/preview_race_character.py -- --motion
& './tools/compose_race_review.ps1'
```

The preset is calibrated to `docs/character_animation/player_body_rigged.blend`, its atlas `assets/textures/char_body.png` and the matching baked position/eye maps `docs/character_head/after/player_body.npz`. Regenerate these together after changing the base. `tools/rebuild.ps1` now saves the required bake maps and runs the race step after retargeting.

## Review and checks

`comparison.png` shows the supplied reference, human base and high elf under matching model lighting. `front.png`, `threequarter.png`, `profile.png`, and `body.png` show the sculpt. The four `*_pose.png` images sample idle, walk, run and sword attack. These are actual Blender renders, not in-game screenshots or generated concept images.

`validation.json` records source preservation, identical rig/weights/topology/UVs, clip count and polygon budget. `godot_validation.log` checks scene selection, fallback, all bone rests and animation names/durations, sampled poses throughout every clip, the player render layer, absence of hair. Existing files edited for integration are preserved under `before/`. The original human models are unchanged.
