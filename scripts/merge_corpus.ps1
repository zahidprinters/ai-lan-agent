param()

$root = Split-Path -Parent $PSScriptRoot
$rawDir = Join-Path $root 'data\raw'
$outputPath = Join-Path $root 'data\input.txt'

Write-Host "[INFO] Merging all .txt files from $rawDir into $outputPath ..." -ForegroundColor Cyan
python -c "from training.corpus import merge_raw_corpus; merge_raw_corpus(r'$rawDir', r'$outputPath')"
Write-Host "[INFO] Merge complete." -ForegroundColor Green
