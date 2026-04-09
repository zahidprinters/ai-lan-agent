param()

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root

Show-ModuleHeader -Title 'AI LAN - REINDEX MODULE' -Task 'Rebuild Run Indexes' -PythonPath $python -TempPath $tempRoot
Write-Host '[STEP 1/1] Rebuilding run index files...' -ForegroundColor Green
& $python (Join-Path $root 'scripts\rebuild_run_index.py')
exit $LASTEXITCODE
