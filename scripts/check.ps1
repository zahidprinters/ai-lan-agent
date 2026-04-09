param()

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root

Show-ModuleHeader -Title 'AI LAN - CHECK MODULE' -Task 'Health Check' -PythonPath $python -TempPath $tempRoot
Write-Host '[STEP 1/2] Verifying core project folders...' -ForegroundColor Green
$required = @('data','models','runs','scripts','tests','tokenizer','training','docs','temp')
foreach ($name in $required) {
    $path = Join-Path $root $name
    if (-not (Test-Path $path)) {
        throw "Missing required project path: $path"
    }
}
Write-Host '[INFO] Core project folders are present.' -ForegroundColor DarkGreen

Write-Host '[STEP 2/2] Running unit smoke tests...' -ForegroundColor Green
& $python -m pytest -m unit
if ($LASTEXITCODE -eq 0) {
    Write-Host '[INFO] Health check passed.' -ForegroundColor Green
}
exit $LASTEXITCODE
