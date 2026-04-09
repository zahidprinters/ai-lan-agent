# Wrapper for scripts/quantize_model.py
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$parent = Split-Path -Parent $root
$python = Join-Path $parent ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

& $python (Join-Path $root "quantize_model.py") $args
exit $LASTEXITCODE
