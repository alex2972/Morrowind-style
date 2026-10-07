param([string]$Reference = 'docs/character_high_elf/reference.png')
Add-Type -AssemblyName System.Drawing
$reviewRoot = Join-Path (Split-Path $PSScriptRoot -Parent) 'docs/character_high_elf'
$sheet = New-Object System.Drawing.Bitmap 1740,900
$graphics = [System.Drawing.Graphics]::FromImage($sheet)
$graphics.Clear([System.Drawing.Color]::FromArgb(24,30,32))
$graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$titleFont = New-Object System.Drawing.Font 'Segoe UI',26
$labelFont = New-Object System.Drawing.Font 'Segoe UI',16
$noteFont = New-Object System.Drawing.Font 'Segoe UI',12
$white = [System.Drawing.Brushes]::WhiteSmoke
$muted = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(179,190,188))
$graphics.DrawString('HIGH ELF / MALE - REFERENCE STUDY',$titleFont,$white,35,24)
$graphics.DrawString('Same base mesh, shared 53-bone skeleton and 73 animation clips.',$noteFont,$muted,38,77)
$panels = @(
    @($Reference,35,175,400,400,'YOUR REFERENCE'),
    @((Join-Path $reviewRoot 'base.png'),475,145,590,656,'SHARED HUMAN BASE'),
    @((Join-Path $reviewRoot 'threequarter.png'),1100,145,590,656,'HIGH ELF VARIANT')
)
foreach ($panel in $panels) {
    $graphics.DrawString($panel[5],$labelFont,$white,[single]$panel[1],113)
    $picture = [System.Drawing.Image]::FromFile([System.IO.Path]::GetFullPath($panel[0]))
    $rectangle = New-Object System.Drawing.Rectangle ([int]$panel[1]),([int]$panel[2]),([int]$panel[3]),([int]$panel[4])
    $graphics.DrawImage($picture,$rectangle)
    $picture.Dispose()
}
$graphics.DrawString('Reference supplied by you; used only for visual direction.',$noteFont,$muted,35,819)
$graphics.DrawString('Model panels: Blender renders of the delivered meshes. Tapered jaw / lean neck / angled brow ridge and eyebrows.',$noteFont,$muted,35,848)
$sheet.Save((Join-Path $reviewRoot 'comparison.png'),[System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose(); $sheet.Dispose(); $titleFont.Dispose(); $labelFont.Dispose(); $noteFont.Dispose(); $muted.Dispose()
