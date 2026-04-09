param(
    [string]$Input = $null,
    [string]$Output = $null
)

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\utils.ps1')
$tempRoot = Set-ProjectTempEnvironment -Root $root
$python = Get-ProjectPython -Root $root

Show-ModuleHeader -Title 'AI LAN - CLEAN DATASET MODULE' -Task 'Clean and Deduplicate Dataset' -PythonPath $python -TempPath $tempRoot

$inputPath = $Input
if (-not $inputPath) {
    $inputPath = (Join-Path $root 'data\input.txt')
}
$outputPath = $Output
if (-not $outputPath) {
    $outputPath = $inputPath -replace '\.txt$', '_cleaned.txt'
}

Write-Host "[STEP 1/1] Cleaning dataset..." -ForegroundColor Green
& $python (Join-Path $root 'scripts\clean_dataset.py') --input $inputPath --output $outputPath
exit $LASTEXITCODE
