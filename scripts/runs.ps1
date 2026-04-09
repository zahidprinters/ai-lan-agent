param(
    [switch]$AllRuns
)

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root
$mode = if ($AllRuns) { 'All Runs' } else { 'Project Runs' }

Show-ModuleHeader -Title 'AI LAN - RUNS MODULE' -Task $mode -PythonPath $python -TempPath $tempRoot
$args = @()
if ($AllRuns) { $args += '--all' }

Write-Host '[STEP 1/1] Loading leaderboard...' -ForegroundColor Green
& $python (Join-Path $root 'scripts\list_runs.py') @args
exit $LASTEXITCODE
