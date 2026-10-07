# Female character reference shape fit

The delivered `assets/models/player_body_female.glb` and
`docs/character_female/player_body_female.blend` use the original mesh reshaped
against the supplied front, side and back turnaround. The original asset,
Blender source, Godot scene and generator are preserved in `before_shape_fit/`.

Changes include a narrower waist/upper pelvis, closer thigh and knee contours,
a less protruding upper glute with a straighter transition into the lower
thigh, a tapered lower jaw/chin, and adjustments to arm length, calf position
and feet. The existing texture, UV layout and topology are retained. The model is now skinned to the male-compatible 53-bone hierarchy; see the
rigging section below. The original shape-fit source remains unrigged.

## Review

- `shape_fit/comparison.png`: reference / original / reshaped, equal body height.
- `shape_fit/silhouette_overlay.png`: cyan = reshaped; pink = original.
- `shape_fit/validation.json`: geometry checks.
- `shape_fit/silhouette_metrics.json`: sampled front contours at a normalized
  638-pixel body height. Outer contour mean error improved from 4.20 to 0.93 px;
  inner leg contour mean error improved from 3.22 to 0.41 px. These measurements
  use the manually measured controls, not an independent 3D ground truth.

The reference is a raster turnaround, so this is a silhouette-based fit rather
than a verified one-to-one reconstruction of an unavailable reference mesh.
Pose, painted shading, faceting and hidden surfaces can still differ.

## Reproduce

`tools/female_reference_shape.py` contains the measured silhouette controls and
geometry fit. `tools/build_character.py -- --female` applies it once after
texture baking and before exporting, so future female builds retain the fit.
It does not affect the male build. The unmodified baked maps remain in the
existing NPZ; the atlas is intentionally baked before the final shape pass.

To recreate the review candidate from the preserved original (no rebake):

```powershell
& .\Blender\blender.exe --background --factory-startup --python-exit-code 1 --python tools/fit_character_female.py
& .\Blender\blender.exe --background --factory-startup --python-exit-code 1 --python tools/validate_character_female.py
& .\Blender\blender.exe --background --factory-startup --python-exit-code 1 --python tools/preview_character_female.py -- docs/character_female/shape_fit/candidate.glb docs/character_female/shape_fit/renders
```

The fit command writes a candidate; it does not overwrite the game asset.
The final candidate was installed into the asset and source paths above,
imported with Godot 4.7.1 and refreshed using:

```powershell
& ..\Godot_v4.7.1-stable_win64_console.exe --headless --editor --path . --import
& ..\Godot_v4.7.1-stable_win64_console.exe --headless --path . --script res://tools/refresh_character.gd -- player_body_female
```

Validation: 2,429 source vertices / 4,850 triangles, identical topology and UVs,
finite coordinates, no collapsed faces, no faces rotated over 90 degrees from
their source normals, and successful Godot import/scene refresh without errors.


## Rigging

- Skinned game asset: `assets/models/player_body_female.glb`.
- Editable rig and packed skin texture: `rig/player_body_female_rigged.blend`.
- Godot prop: `scenes/props/player_body_female.tscn`, with Skeleton3D and Skin.
- Rig/deformation preview: `rig/rig_preview.png`.
- Pre-rig asset and scene: `rig/before/`.

All 53 joint names and parents exactly match `assets/models/player_body.glb`,
including Root, pelvis/spine, neck/head, clavicles, limbs, fingers and toes.
Bone rest positions fit the female proportions. Existing male animations
should be retargeted for these rest positions rather than assuming identical
bone lengths and bind matrices. This pass adds the rig and skin only.

Weights are transferred barycentrically from the female MakeHuman anatomical
source, with at most four normalized influences per vertex. The weight source
and bones pass through the same silhouette deformation field as the female
body, using a regenerated low-poly cage; the delivered body is not reshaped
again. The whole assembly is grounded at the soles, like the male model.

Validation covers the exported GLB: identical joint names/parents, no unweighted
vertices, maximum weight-sum error below 0.000001, preserved per-corner UVs,
rest shape error below 0.000001 m after grounding, and finite deformations in
knee/elbow and reaching/finger poses. Godot import and scene refresh succeeded.
The male GLB was not modified. Reports and logs are in `rig/`.

Rebuild the female rig after rebuilding her mesh:

```powershell
& .\Blender\blender.exe --background --python-exit-code 1 --python tools/rig_character.py -- --female
& ..\Godot_v4.7.1-stable_win64_console.exe --headless --editor --path . --import
& ..\Godot_v4.7.1-stable_win64_console.exe --headless --path . --script res://tools/refresh_character.gd -- player_body_female
```

The full `tools/rebuild.ps1` now includes this step. To recheck the exported skin
and rerender joint poses, run `tools/validate_female_rig.py` with bundled Blender.


## Animations

The female rig carries the same 73 clips as the male: idle, walk, run, sprint, crouch, jumps, roll, sword combos, block and shield, punches, hits, knockback, death, spells, swimming, interactions and emotes. They are retargeted from the CC0 Quaternius Universal Animation Libraries 1 and 2 (plus six clips from the MorrowindOnline rig) onto her own rest skeleton:

```powershell
& .\Blenderlender.exe --background --python-exit-code 1 --python tools/retarget_animations.py -- --female
```

For her, idle, walk and run add a hip sway: the pelvis tilts up over the supporting leg, the legs keep their direction and the spine counters to keep the chest level (`HIP_SWAY` in the script). Clip durations and measured travel speeds (walk 1.09 m/s, run 5.07 m/s) are in `rig/clips.json`. `tools/rebuild.ps1` runs this after the female rig step.


## Neck, bust and gait refinement

The current asset incorporates the user's 73-clip animation pass plus a small
additional walk/run layer. The other 71 action data blocks were preserved
exactly. The animated input GLB, rigged Blender source, clip metadata and
retarget script are backed up in `refinement/before/`.

- Neck: 4.5 cm shorter at the head, blending through the neck into the shoulders.
  The head keeps its shape and the neck/head rest bones follow the correction.
- Bust: broader volume, inward shift toward the sternum, and less concentrated
  projection at the tips; the bandeau uses the existing UVs and texture.
- Walk/run: retain the user's hip-sway layer, add 1.1 / 0.55 degrees of support-led
  hip tilt and mild pelvic counter-rotation, narrow foot paths by 10% / 6%, and
  bring the arm carriage in slightly. A two-bone leg solve retains foot height,
  forward travel and orientation while accommodating the new pelvis motion.

`female_body_refinements.py` and `female_gait_polish.py` hold the new controls.
They are called from the existing shape-fit and retargeting pipelines, so normal
female rebuilds keep these changes. Male builds are unaffected.
`refine_female_character.py` reconstructs this revision from the preserved input;
it changes the existing walk/run clips directly instead of regenerating all clips.

Review `refinement/body_comparison.png`, `refinement/walk_comparison.gif`, and
`refinement/run_comparison.gif` (before/after). The validation report confirms
73 clips, only two changed action data blocks, identical topology/UVs/weights,
and foot-target error below one micrometre. Walk closes exactly; run retains
the original approximately 3.9 mm endpoint discrepancy rather than introducing
a new loop seam. Godot import and female-scene refresh succeeded.


## Body restored (refinement reverted)

The neck/bust refinement was rejected. `tools/restore_female_previous_body.py` put the pre-refinement body and rest skeleton back exactly (from `refinement/before/`, vertex difference 0) while keeping all 73 current clips, including the walk/run gait polish, unchanged (checked by hash). The state before this restore is in `restore_previous/before/`. `APPLY_BODY_REFINEMENTS = False` in `tools/female_reference_shape.py` keeps future female builds on this body; the gait polish stays active.
