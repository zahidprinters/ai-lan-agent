param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root
$env:AI_LAN_MODEL_TYPE = 'bigram'

Show-ModuleHeader -Title 'AI LAN - BIGRAM TRAIN MODULE' -Task 'Train Bigram Baseline' -PythonPath $python -TempPath $tempRoot
Write-Host '[STEP 1/1] Launching bigram training pipeline...' -ForegroundColor Green
& $python (Join-Path $root 'training\train_char_model.py') @Args
$code = $LASTEXITCODE
Remove-Item Env:AI_LAN_MODEL_TYPE -ErrorAction SilentlyContinue
exit $code
