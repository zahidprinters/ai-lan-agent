param()

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root

Show-ModuleHeader -Title 'AI LAN - COMPARE MODULE' -Task 'Compare Checkpoints' -PythonPath $python -TempPath $tempRoot
Write-Host '[STEP 1/1] Reading checkpoint metadata...' -ForegroundColor Green
& $python (Join-Path $root 'scripts\compare_checkpoints.py')
exit $LASTEXITCODE
