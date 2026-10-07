# Player rig and locomotion

## Assets

- Game model: `assets/models/player_body.glb`.
- Godot scene: `scenes/props/player_body.tscn` (Skeleton3D, weighted mesh and AnimationPlayer).
- Editable source: `docs/character_animation/player_body_rigged.blend`, with packed skin texture.
- Original unrigged model and changed source files: `docs/character_animation/before/`.

The current head, body geometry and UVs are retained. Anatomical weights are projected barycentrically from the matching MakeHuman source onto the game mesh, normalized to four influences per vertex. The rig has 53 named bones: root, pelvis, spine, neck/head, clavicles, arms, hands, individual fingers, legs, feet and toes. It uses linear blend skinning, matching glTF/Godot. The model is grounded at the soles.

## Animation clips

`tools/retarget_animations.py` retargets clips from three sources in `tools/anim_source/` onto this rig (73 clips). It runs after `tools/rig_character.py` and replaces that script's procedural clips.

- **Quaternius Universal Animation Library 1 and 2**, Standard ([pack 1](https://quaternius.com/packs/universalanimationlibrary.html), [pack 2](https://opengameart.org/content/universal-animation-library-2); both CC0): `quaternius_ual_standard.glb`, `quaternius_ual2_standard.glb`, with licences alongside. These provide nearly every clip.
- **`low_poly_human_rigged.glb`** (MorrowindOnline project): only what the packs lack, which is walk_backward, strafe_left, strafe_right, combat_idle (fists up), cast_spell and fall.

How the motion is transferred:
- Legs, plus the Quaternius arms and fingers (that rig is T-posed), copy the source bone directions.
- The torso, head and clavicles copy rotation changes from rest, so the player keeps his own posture.
- Pelvis travel scales with leg length, and every clip is grounded on the player's soles.
- Root-bone travel is cancelled, so every clip plays in place (some Quaternius clips move the root even outside their `_RM` variants). The `_RM` root-motion variants are not imported.
- idle, walk and run get an extra polish layer (heroic stance, breathing, less torso twist); see `polish()` and `TWEAKS`. The run is the Quaternius jog softened into an MMO jog: a shorter stride, lower knee kick and less bounce, with the thighs and calves pulled 40% / 30% toward a straight leg. The original full-stride version is close to `sprint`.

Looping clips are exported with a `_loop` suffix. Godot's importer removes the suffix and sets them to loop, so in the game every clip has the plain name below.

| Group | Clips (looping in **bold**) |
| --- | --- |
| Locomotion | **idle**, **walk** (1.13 m/s), **run** (4.97 m/s), **sprint** (9.49 m/s), **walk_backward**, **strafe_left**, **strafe_right**, **crouch_idle**, **crouch_walk** (sneak), roll, **walk_carry**, slide_start / **slide** / slide_exit |
| Jumping and falling | jump_start / **jump** (airborne) / jump_land, flip_jump_start / **flip_jump** / flip_jump_land, **fall** |
| Sword | **sword_idle**, sword_attack, sword_slash_a / _b / _c, sword_slash_a_recover / _b_recover, sword_combo (three hits) |
| Shield and block | **shield_idle**, block, shield_bash, shield_break |
| Unarmed | **combat_idle**, punch_enter (guard up), punch_jab, punch_cross, punch_hook, punch_hook_recover |
| Getting hit | hit_chest, hit_head, knockback, get_up, death |
| Magic | spell_enter / **spell_idle** (channel) / spell_cast / spell_exit, cast_spell |
| Swimming | **swim_idle**, **swim** |
| Interaction | interact, pick_up, open_chest, drink, throw, sit_down / **sit_idle** / **sit_talk** / stand_up, **push**, kneel_work |
| Gathering | **chop**, harvest, plant_seed, watering |
| Idles and emotes | **talk**, **idle_torch**, **idle_lantern**, **idle_fold_arms**, emote_yes, **emote_no**, **dance** |

Travel speeds are measured from the planted foot and written to `clips.json`, together with durations and sources. The controller's `WALK_CLIP_SPEED` / `RUN_CLIP_SPEED` match playback to movement speed. Run speed is 5.0 m/s and walk is 1.45 m/s. The game currently plays idle, walk, run and the jump set: jump_start on take-off (its pre-crouch is skipped because the physics jump is instant), the airborne `jump` loop for long airtime, `jump` / `fall` when walking off a ledge, and jump_land on touchdown (shortened when you keep moving). The rest of the clips are ready for gameplay code (`AnimationPlayer.play('sword_combo')` and so on). The sword and shield clips animate empty hands, since no weapon model is attached yet. Previews: `idle.gif`, `walk.gif`, `run.gif`.

## Godot behavior

Press Tab to see the body, WASD to walk, Shift to run. The controller uses actual horizontal velocity to control playback rate, accounts for the existing 0.94 model scale, and blends clip changes over 0.18 seconds. Walk/run transitions preserve normalized stride phase. The body faces its travel direction. Pausing freezes animation. Idle is used while airborne or swimming; dedicated jump, swim, crouch and directional strafe clips are not part of this pass. Foot contacts are authored for level ground; terrain foot IK is not included.

Default movement speeds are 1.45 m/s walking and 6.0 m/s running. Sneaking now uses 0.95 m/s. These remain exported controller properties.

## Rebuild

Run from the project root in PowerShell, after any geometry/texture rebuild:

```powershell
& '.\Blender\blender.exe' --background --python-exit-code 1 --python tools\rig_character.py
& '.\Blender\blender.exe' --background --python-exit-code 1 --python tools\retarget_animations.py
& 'Z:\godot\Godot_v4.7.1-stable_win64_console.exe' --headless --editor --path . --import
& 'Z:\godot\Godot_v4.7.1-stable_win64_console.exe' --headless --path . --script res://tools/refresh_character.gd
```

The full `tools/rebuild.ps1` includes the rigging step. MPFB must be enabled, so do not add `--factory-startup`.

To render the animation previews:

```powershell
& '.\Blender\blender.exe' --background --python-exit-code 1 --python tools\preview_character_animation.py -- --loops
```

The preview images are Blender renders. Godot import and character scene refresh logs are saved in this directory.
