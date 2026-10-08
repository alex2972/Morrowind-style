# Female High Elf

Bald female High Elf variant of the current female character. The supplied reference guides the tapered chin and jaw, high cheekbones, angled brows and pointed ears. Skin is golden amber and eyes are gold. No hair is included.

## Assets and selection

- `assets/models/player_high_elf_female.glb`: 4,850 triangles, 53 bones, 73 animation clips.
- `assets/textures/char_high_elf_female.png`: 1024-square race atlas, retaining the female UV layout.
- `scenes/props/player_high_elf_female.tscn`: imported game scene.
- `docs/character_high_elf_female/high_elf_female.blend`: editable rigged model with packed texture and actions.
- `tools/high_elf_female.json`: adjustable female shape and colour preset.
- `tools/race_high_elf_female.py`: female-specific sculpt and paint functions used by the shared race builder.

Selecting Female + High Elf now chooses this model in creation previews, the world player, other actors, and the portrait. Male High Elf selection retains its existing model. Other races keep their original male/female models.

## Preservation

The original female source is `docs/character_female/rig/player_body_female_rigged.blend`. It remains unchanged. The sculpt is restricted to the head and neck; all body vertices below 1.43 m retain their original coordinates. Topology, UVs, vertex weights and all 53 bind transforms are retained. The original female animation set is exported intact; these are the female-compatible versions of the 73 clips, not male clips applied to different bind proportions. Runtime race height is the same `races.scale` as the male (1.07 for the High Elf, a vertical-only stretch), so a female High Elf stands 7% taller than a female Human with 7% longer legs; set the value in the `races` table.

The atlas is derived from `assets/textures/char_body_female.png` and its original bake maps at `docs/character_female/player_body_female.npz`. Painting uses the bake-space coordinates; sculpting uses the current fitted model's coordinates. This distinction preserves the earlier female proportion and neck adjustments.

## Rebuild and review

From the project root:

```powershell
& './Blender/blender.exe' --background --python-exit-code 1 --python tools/build_race_character.py -- --preset tools/high_elf_female.json
& 'Z:/godot/Godot_v4.7.1-stable_win64_console.exe' --headless --editor --path . --import
& 'Z:/godot/Godot_v4.7.1-stable_win64_console.exe' --headless --path . --script res://tools/refresh_character.gd -- player_high_elf_female
& 'Z:/godot/Godot_v4.7.1-stable_win64_console.exe' --headless --path . --script res://tools/verify_race_character.gd
& './Blender/blender.exe' --background --python-exit-code 1 --python tools/preview_race_character.py -- --female
& './Blender/blender.exe' --background --python-exit-code 1 --python tools/preview_race_character.py -- --female --base
& './Blender/blender.exe' --background --python-exit-code 1 --python tools/preview_race_character.py -- --female --motion
& './tools/compose_race_review.ps1' -Female
```

`comparison.png` shows the reference, female base, and race variant. Front, profile, three-quarter, full-body and four animation-pose renders are also included. These are Blender renders of the delivered model. `validation.json` records source preservation and geometry/rig checks; `godot_validation.log` checks both male and female race selection, bone rests, clip names/durations, sampled animation poses, fallback for other races, and absence of hair. The shared full rebuild includes both High Elf presets.
