param()

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root

Show-ModuleHeader -Title 'AI LAN - SETUP MODULE' -Task 'Create Or Refresh Environment' -TempPath $tempRoot
Write-Host '[STEP 1/4] Checking Python installation...' -ForegroundColor Green
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python is not available in PATH. Install Python 3.11+ and try again.'
}

$venvPython = Join-Path $root '.venv\Scripts\python.exe'
$devRequirements = Join-Path $root 'dev-requirements.txt'

Write-Host '[STEP 2/4] Creating virtual environment if needed...' -ForegroundColor Green
if (-not (Test-Path $venvPython)) {
    & python -m venv (Join-Path $root '.venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
else {
    Write-Host '[INFO] Virtual environment already exists.' -ForegroundColor DarkGreen
}

Write-Host '[STEP 3/4] Upgrading pip...' -ForegroundColor Green
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '[STEP 4/4] Installing runtime and development tools...' -ForegroundColor Green
$requirements = Join-Path $root 'requirements.txt'
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $venvPython -m pip install -r $devRequirements
if ($LASTEXITCODE -eq 0) {
    Write-Host '[INFO] Environment setup completed successfully.' -ForegroundColor Green
}
exit $LASTEXITCODE
