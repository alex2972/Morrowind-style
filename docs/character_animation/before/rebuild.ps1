param([string]$GodotPath = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (-not $GodotPath) {
    $engine = Get-ChildItem -LiteralPath (Split-Path $projectRoot -Parent) -Filter 'Godot*_console.exe' -File | Select-Object -First 1
    if (-not $engine) { throw 'Pass -GodotPath with the path to your Godot 4.7 console executable.' }
    $GodotPath = $engine.FullName
}
$blenderPath = Join-Path $projectRoot 'Blender\blender.exe'
if (-not (Test-Path -LiteralPath $blenderPath)) { throw "Blender executable not found: $blenderPath" }
Push-Location $projectRoot
try {
    python tools/build_textures.py
    if ($LASTEXITCODE -ne 0) { throw 'Texture build failed. Install numpy and Pillow for your Python interpreter.' }
    python tools/build_terrain.py
    if ($LASTEXITCODE -ne 0) { throw 'Terrain/layout build failed.' }
    python tools/build_audio.py
    if ($LASTEXITCODE -ne 0) { throw 'Audio build failed.' }
    & $blenderPath --background --factory-startup --python tools/build_models.py
    if ($LASTEXITCODE -ne 0) { throw 'Blender model build failed.' }
    # MPFB (MakeHuman) is a user extension, so the character build loads the user's Blender settings
    & $blenderPath --background --python-exit-code 1 --python tools/build_character.py
    if ($LASTEXITCODE -ne 0) { throw 'Blender character build failed.' }
    & $GodotPath --headless --editor --path $projectRoot --import
    if ($LASTEXITCODE -ne 0) { throw 'Godot resource import failed.' }
    & $GodotPath --headless --path $projectRoot --script res://tools/build_world.gd
    if ($LASTEXITCODE -ne 0) { throw 'World build failed.' }
    Write-Output 'Veyr rebuilt. Open project.godot and press F5.'
} finally { Pop-Location }
