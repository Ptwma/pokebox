# Pokebox HD cards — upscales every card image with Real-ESRGAN (runs on your GPU, resumable).
# Output: POKEMON\pokemon-card-scraper\pokemon_cards\images_hd\<same name>.webp  (the game uses these automatically)
param([ValidateSet('fast','max')][string]$Quality = 'fast', [int]$Batch = 400)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$exe  = Join-Path $here 'realesrgan\realesrgan-ncnn-vulkan.exe'
$root = (Resolve-Path (Join-Path $here '..\..')).Path
$in   = Join-Path $root 'pokemon-card-scraper\pokemon_cards\images'
$out  = Join-Path $root 'pokemon-card-scraper\pokemon_cards\images_hd'
if (-not (Test-Path $exe)) {
  Write-Host "Real-ESRGAN not found at $exe" -ForegroundColor Yellow
  Write-Host "1) Download 'realesrgan-ncnn-vulkan-20220424-windows.zip' from https://github.com/xinntao/Real-ESRGAN/releases"
  Write-Host "2) Extract it so this file exists: $exe"
  Write-Host "3) Run upscale_cards.bat again."
  Read-Host 'Press Enter to close'; exit 1
}
if ($Quality -eq 'max') { $model = 'realesrgan-x4plus-anime'; $scale = 4 } else { $model = 'realesr-animevideov3'; $scale = 2 }
New-Item -ItemType Directory -Force -Path $out | Out-Null
$tmp = Join-Path $env:TEMP 'pokebox_upscale_batch'
$all = @(Get-ChildItem -Path $in -File | Where-Object { $_.Extension -match '\.(jpg|jpeg|png|webp)$' })
$todo = @($all | Where-Object { -not (Test-Path (Join-Path $out ($_.BaseName + '.webp'))) })
Write-Host ("{0} cards total, {1} already done, {2} to upscale ({3}, x{4})" -f $all.Count, ($all.Count - $todo.Count), $todo.Count, $model, $scale) -ForegroundColor Cyan
$done = 0; $sw = [Diagnostics.Stopwatch]::StartNew()
for ($i = 0; $i -lt $todo.Count; $i += $Batch) {
  if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
  New-Item -ItemType Directory -Path $tmp | Out-Null
  $chunk = @($todo[$i..([Math]::Min($i + $Batch, $todo.Count) - 1)])
  foreach ($f in $chunk) { Copy-Item $f.FullName (Join-Path $tmp $f.Name) }
  & $exe -i $tmp -o $out -n $model -s $scale -f webp | Out-Null
  $done += $chunk.Count
  $rate = $done / [Math]::Max(1, $sw.Elapsed.TotalSeconds); $left = ($todo.Count - $done) / [Math]::Max(0.01, $rate)
  Write-Host ("{0}/{1} done - about {2:N0} min left" -f $done, $todo.Count, ($left / 60))
}
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
Write-Host 'Finished. Restart Pokebox - HD cards are used automatically.' -ForegroundColor Green
Read-Host 'Press Enter to close'
