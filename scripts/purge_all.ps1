param()

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root

Show-ModuleHeader -Title 'AI LAN - PURGE MODULE' -Task 'Purge All Cache, Temp, and Artifacts' -TempPath $tempRoot
Write-Host '[STEP 1/4] Removing Python __pycache__ folders...' -ForegroundColor Green
Get-ChildItem $root -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host '[STEP 2/4] Removing .mypy_cache folders...' -ForegroundColor Green
Get-ChildItem $root -Recurse -Directory -Filter .mypy_cache -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host '[STEP 3/4] Removing temp/ contents...' -ForegroundColor Green
$tempDir = Join-Path $root 'temp'
if (Test-Path $tempDir) {
    Get-ChildItem $tempDir -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne '.gitkeep' } |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host '[STEP 4/4] Removing .pytest_cache folders...' -ForegroundColor Green
Get-ChildItem $root -Recurse -Directory -Filter .pytest_cache -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host '[INFO] Purged all cache, mypy, pytest, and temp data.' -ForegroundColor Green
