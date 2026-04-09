param()

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root

Show-ModuleHeader -Title 'AI LAN - DATA REPORT MODULE' -Task 'Dataset Report' -PythonPath $python -TempPath $tempRoot
Write-Host '[STEP 1/1] Analyzing active dataset...' -ForegroundColor Green
& $python (Join-Path $root 'scripts\data_report.py')
exit $LASTEXITCODE
