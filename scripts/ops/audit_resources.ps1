param()

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root

Show-ModuleHeader -Title 'AI LAN - RESOURCE AUDIT' -Task 'Regenerate Local Resource Inventory' -PythonPath $python -TempPath $tempRoot

& $python (Join-Path $root 'scripts\regenerate_resource_inventory.py')
exit $LASTEXITCODE