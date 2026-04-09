param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root
$env:AI_LAN_MODEL_TYPE = 'bigram'

Show-ModuleHeader -Title 'AI LAN - BIGRAM GENERATE MODULE' -Task 'Generate With Bigram Baseline' -PythonPath $python -TempPath $tempRoot
Write-Host '[STEP 1/1] Launching bigram generation pipeline...' -ForegroundColor Green
& $python (Join-Path $root 'training\generate.py') @Args
$code = $LASTEXITCODE
Remove-Item Env:AI_LAN_MODEL_TYPE -ErrorAction SilentlyContinue
exit $code
