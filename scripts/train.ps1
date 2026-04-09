param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root

Show-ModuleHeader -Title 'AI LAN - TRAINING MODULE' -Task 'Training Character Model' -PythonPath $python -TempPath $tempRoot
Write-Host '[STEP 1/1] Launching training pipeline...' -ForegroundColor Green
& $python (Join-Path $root 'training\train_char_model.py') @Args
exit $LASTEXITCODE
