param(
    [ValidateSet('all', 'unit', 'integration')]
    [string]$Suite = 'all'
)

$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$root;$env:PYTHONPATH"
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root


Show-ModuleHeader -Title 'AI LAN - TEST MODULE' -Task "Run $Suite Tests" -PythonPath $python -TempPath $tempRoot

# [STEP 0] Enforce temp file policy
Write-Host '[STEP 0] Checking temp file policy...' -ForegroundColor Green
& $python (Join-Path $root 'scripts/check_temp_policy.py')
if ($LASTEXITCODE -ne 0) {
    Write-Host '[ERROR] Temp file policy violation. Aborting tests.' -ForegroundColor Red
    exit $LASTEXITCODE
}

$pytestArgs = @('-m', 'pytest')

switch ($Suite) {
    'unit' { $pytestArgs += @('-m', 'unit') }
    'integration' { $pytestArgs += @('-m', 'integration') }
    default { }
}

Write-Host '[STEP 1/1] Launching pytest...' -ForegroundColor Green
& $python @pytestArgs
if ($LASTEXITCODE -eq 0) {
    Write-Host '[INFO] Test run completed successfully.' -ForegroundColor Green
}
exit $LASTEXITCODE
