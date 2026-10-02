# Copies the game into the Android project and makes phone-sized copies of all card images.
# Run by build-apk.bat. Safe to re-run: cards already converted are skipped.
param([int]$Width = 320, [int]$Quality = 70, [int]$Jobs = 4)
$ErrorActionPreference = 'Stop'
$root  = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path          # ...\POKEMON
$game  = Join-Path $root 'pokebox-game'
$cards = Join-Path $root 'pokemon-card-scraper\pokemon_cards\images'
$www   = Join-Path $PSScriptRoot '..\app\src\main\assets\www'
New-Item -ItemType Directory -Force $www | Out-Null
$www = (Resolve-Path $www).Path

Write-Host '[1/2] Copying game files...'
robocopy $game (Join-Path $www 'pokebox-game') /MIR /XD tools design .git /XF *.vbs *.bat *.lnk *.ps1 *.exe README.md /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }

Write-Host "[2/2] Card images -> ${Width}px JPEG q$Quality (first time takes a few minutes)..."
$dst = Join-Path $www 'pokemon-card-scraper\pokemon_cards\images'
New-Item -ItemType Directory -Force $dst | Out-Null
if (-not (Test-Path -LiteralPath $cards)) { Write-Warning "Card images folder not found: $cards  - the APK will be built without card pictures."; return }
$todo = @(Get-ChildItem -LiteralPath $cards -File | Where-Object { -not (Test-Path -LiteralPath (Join-Path $dst $_.Name)) } | ForEach-Object FullName)
Write-Host "  $($todo.Count) to convert"
if ($todo.Count) {
  $work = {
    param($list, $dst, $W, $Q)
    Add-Type -AssemblyName System.Drawing
    $enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
    $ep = New-Object System.Drawing.Imaging.EncoderParameters 1
    $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]$Q)
    foreach ($src in $list) {
      try {
        $img = [System.Drawing.Image]::FromFile($src)
        $w = [Math]::Min($W, $img.Width); $h = [int][Math]::Round($img.Height * $w / $img.Width)
        $bmp = New-Object System.Drawing.Bitmap $w, $h
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $g.DrawImage($img, 0, 0, $w, $h)
        $bmp.Save((Join-Path $dst ([IO.Path]::GetFileName($src))), $enc, $ep)
        $g.Dispose(); $bmp.Dispose(); $img.Dispose()
      } catch { Write-Warning "skip $src : $_" }
    }
  }
  $chunk = [Math]::Ceiling($todo.Count / $Jobs); $jl = @()
  for ($i = 0; $i -lt $Jobs; $i++) { $part = $todo | Select-Object -Skip ($i * $chunk) -First $chunk; if ($part) { $jl += Start-Job -ScriptBlock $work -ArgumentList (,$part), $dst, $Width, $Quality } }
  while (($jl | Where-Object State -eq 'Running').Count) {
    $done = (Get-ChildItem -LiteralPath $dst -File).Count
    Write-Progress -Activity 'Converting card images' -Status "$done files ready" -PercentComplete ([Math]::Min(100, $done * 100 / [Math]::Max(1, $done + $todo.Count)))
    Start-Sleep -Seconds 3
  }
  $jl | Receive-Job | Out-Null; $jl | Remove-Job
}
$mb = [Math]::Round(((Get-ChildItem -LiteralPath $dst -File | Measure-Object Length -Sum).Sum) / 1MB)
Write-Host "  cards ready: $((Get-ChildItem -LiteralPath $dst -File).Count) files, $mb MB"
