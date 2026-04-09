param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root

Show-ModuleHeader -Title 'AI LAN - GENERATION MODULE' -Task 'Generate Text' -PythonPath $python -TempPath $tempRoot
Write-Host '[STEP 1/1] Launching generation pipeline...' -ForegroundColor Green
& $python (Join-Path $root 'training\generate.py') @Args
exit $LASTEXITCODE
