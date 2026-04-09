param()

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root

Show-ModuleHeader -Title 'AI LAN - CLEAN MODULE' -Task 'Clean Cache And Temp Data' -TempPath $tempRoot
Write-Host '[STEP 1/3] Removing Python cache folders...' -ForegroundColor Green
Get-ChildItem $root, (Join-Path $root 'scripts'), (Join-Path $root 'tokenizer'), (Join-Path $root 'training'), (Join-Path $root 'tests') -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $root '.pytest_cache') -Recurse -Force -ErrorAction SilentlyContinue

# [STEP 1.1] Remove .mypy_cache folders
Get-ChildItem $root -Recurse -Directory -Filter .mypy_cache -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host '[STEP 2/2] Cleaning project temp folder...' -ForegroundColor Green
Get-ChildItem $tempRoot -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne '.gitkeep' } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host '[INFO] Cleaned local cache folders and project temp data.' -ForegroundColor Green
